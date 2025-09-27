import asyncio
import json
import uuid
from typing import Any, Callable, Optional, Coroutine
from functools import wraps

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from redis.asyncio import Redis

from Config import setup_logger, DBSettings
from Database.Client import DatabaseClient

logger = setup_logger(
    'fastapi_app',
    log_format='%(levelname)s:     [%(name)s] %(asctime)s | %(message)s'
)

engine_cache = {}
session_cache = {}


class DBProxy:
    """
    DBProxy wraps the database and Redis interface:
    - get_or_cache: retrieves an object from Redis, or if not, from the database, and stores it in Redis
    - update_and_cache: updates the object in the database and directly in Redis
    """
    def __init__(self, redis: Redis):
        self._open_sessions = []
        self.db_settings = DBSettings()
        self.redis = redis

    async def get_db(self, db_name: str):
        if db_name not in session_cache:
            url = self.db_settings.get_db_url(db_name)
            engine = create_async_engine(url,
                                         future=True,
                                         echo=False,
                                         pool_pre_ping=True,
                                         pool_recycle=300,
                                         pool_size=10,
                                         max_overflow=20,
                                         )
            engine_cache[db_name] = engine
            session_cache[db_name] = async_sessionmaker(
                bind=engine, class_=AsyncSession, expire_on_commit=False
            )

        session = session_cache[db_name]()
        self._open_sessions.append(session)
        return session

    async def close_all(self):
        for session in self._open_sessions:
            await session.close()
        self._open_sessions.clear()

    # -----------------------------
    # Redis utils
    # -----------------------------
    async def redis_set(self, key: str, value: Any, ttl: Optional[int] = None):
        data = json.dumps(value)
        if ttl:
            await self.redis.setex(key, ttl, data)
        else:
            await self.redis.set(key, data)
        logger.debug(f"Redis SET {key} -> {value}")

    async def redis_get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        logger.debug(f"Redis GET {key} -> {data}")
        return json.loads(data) if data else None

    async def redis_delete(self, key: str):
        deleted = await self.redis.delete(key)
        logger.debug(f"Redis DEL {key} -> deleted={deleted}")

    async def redis_expire(self, key: str, ttl: int):
        await self.redis.expire(key, ttl)
        logger.debug(f"Redis EXPIRE {key} -> {ttl}s")

    # -----------------------------
    # DB + Cache logic
    # -----------------------------
    async def get_or_cache(self, key: str, db_name: str, query_func: Callable[[AsyncSession], Coroutine[Any, Any, Any]],
        ttl: int = 60) -> Optional[Any]:

        cached = await self.redis_get(key)
        if cached:
            logger.debug(f"{key} returned from cache")
            return cached

        session = await self.get_db(db_name)
        result = await query_func(session)
        if result:
            await self.redis_set(key, result, ttl)
            logger.debug(f"{key} returned from database")

        return result

    async def update_and_cache(self, key: str, db_name: str, update_func: Callable[[AsyncSession], Coroutine[Any, Any, Any]],
            ttl: int = 60, related_pattern: Optional[str] = None) -> Any:

        session = await self.get_db(db_name)
        result = await update_func(session)
        await session.commit()

        await self.redis_delete(key)
        logger.debug(f"Redis DEL {key} (main key)")

        if related_pattern:
            async for rk in self.redis.scan_iter(match=related_pattern):
                await self.redis_delete(rk)
                logger.debug(f"Redis DEL {rk} (related key via pattern {related_pattern})")

        if result:
            await self.redis_set(key, result, ttl)
            logger.debug(f"{key} updated in database and cache")

        return result

# -----------------------------
# Decorator for simplification
# -----------------------------
def cache_query(key_template: str, ttl: int = 60, update: bool = False, related_pattern: Optional[str] = None):
    """
    Wrapper for methods in endpoints:
    - If update=False → get_or_cache
    - If update=True → update_and_cache

    Example:
    @cache_query("registration:{reg}", ttl=120)
    async def get_registration(session, reg): ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request")
            if not request:
                raise ValueError("Request must be passed to the endpoint")

            key = key_template.format(**kwargs)
            db: DBProxy = request.app.state.db_proxy
            db_name = kwargs.get("db_name")

            _related_pattern = related_pattern.format(**kwargs) if related_pattern else None

            if update:
                return await db.update_and_cache(key, db_name, lambda session: func(session, *args, **kwargs), ttl, related_pattern=_related_pattern)
            else:
                return await db.get_or_cache(key, db_name, lambda session: func(session, *args, **kwargs), ttl)

        return wrapper
    return decorator


def register_middlewares(app):
    @app.on_event("startup")
    async def startup_event():
        username, password, host, port = DBSettings().get_reddis_credentials()
        logger.info("Startup initiated...")
        app.state.redis = Redis(username=username, password=password, host=host, port=port, decode_responses=True)
        app.state.db_client = DatabaseClient()
        app.state.db_proxy = DBProxy(app.state.redis)
        logger.info("Redis and DatabaseClient initialized")

        try:
            from .FindCSV import find_csv_loop
            from .FindJSON import find_json_loop
            from Scheduler import Scheduler
            from Scheduler.jobs import jobs, update_subscription_job

            scheduler = Scheduler(jobs=jobs)
            scheduler.start()
            asyncio.create_task(find_json_loop(app.state.db_client))
            asyncio.create_task(find_csv_loop(app.state.db_client))
            asyncio.create_task(update_subscription_job(
                db_proxy=app.state.db_proxy,
                change_type="created",
                resource="users",
            ))

        except Exception as _ex:
            logger.warning(f"Error starting background tasks: {_ex}")
        finally:
            logger.info("Startup completed. Welcome :O")

    # Middleware for requests  db/cache
    @app.middleware("http")
    async def db_cache_requests(request: Request, call_next):
        request.state.redis = app.state.redis
        request.state.db = app.state.db_proxy
        request.state.db._open_sessions.clear()
        response = await call_next(request)
        await request.state.db.close_all()
        return response

    # Middleware for requests logging and db/cache
    @app.middleware("http")
    async def log_and_db_requests(request: Request, call_next):
        start_time = asyncio.get_event_loop().time()
        request.state.redis = app.state.redis
        request.state.db, _id = DBProxy(app.state.redis)

        try:
            response = await call_next(request)
        finally:
            await request.state.db.close_self(_id)

        duration = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"{request.method} {request.url.path} completed_in={duration:.2f}s "
            f"status_code={response.status_code}"
        )
        return response

    # Middleware for add correlation id to requests
    @app.middleware("http")
    async def add_correlation_id(request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Custom exception handler
    @app.exception_handler(Exception)
    async def custom_exception_handler(request: Request, exc: Exception):
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.error(f"Unhandled error: {exc} \n CorrelationID = {correlation_id}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error", "correlationId": correlation_id, "code": 500},
        )

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutdown initiated...")
        logger.info("Closing redis connection...")
        await app.state.redis.close()
        logger.info("Closing database connection...")
        await app.state.db_client.dispose()
        logger.info("Shutdown completed. Bye!")


__all__ = ["register_middlewares", "cache_query", "DBProxy"]
