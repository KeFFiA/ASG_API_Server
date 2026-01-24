import asyncio
import functools
import inspect
import json
import time
import uuid
from functools import wraps
from typing import Any, Callable, Optional, Coroutine

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from Config import setup_logger, DBSettings, ENABLE_PERFORMANCE_LOGGER
from Database import DatabaseClient, Registrations
from Schemas import ErrorValidationResponse, ErrorValidObject, ErrorResponse, DetailField
from Schemas.Enums.service import FilesExtensionEnum
from Utils.FilesFinder import Finder

logger = setup_logger(
    'fastapi_app',
    log_format='%(levelname)s:     [%(name)s] %(asctime)s | %(message)s'
)

perf_dec_logger = setup_logger(
    "performance",
    log_format="%(levelname)s:     [%(name)s] %(asctime)s | %(message)s"
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

    async def update_and_cache(self, key: str, db_name: str,
                               update_func: Callable[[AsyncSession], Coroutine[Any, Any, Any]],
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
                return await db.update_and_cache(key, db_name, lambda session: func(session, *args, **kwargs), ttl,
                                                 related_pattern=_related_pattern)
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
            from .CSVFiles import process_csv_file
            from .JSONFiles import process_json_file
            from .EXCELFiles import process_excel_file
            from .CiriumFiles import process_cirium_file
            from Scheduler import Scheduler
            from Scheduler.jobs import jobs, update_subscription_job
            from Config import FILES_PATH, EXCEL_FILES_PATH, CIRIUM_FILES_PATH
            from API.FlightRadarAPI.LiveFlightsAPI import FlightPollingStorage

            app.state.scheduler = Scheduler(jobs=jobs)
            app.state.scheduler.start()

            finder = Finder()

            asyncio.create_task(finder.start_loop(  # JSON PROCESSOR
                db_client=app.state.db_client,
                func=process_json_file,
                path=FILES_PATH,
                extension=FilesExtensionEnum.JSON,
                db="service"
            ))
            asyncio.create_task(finder.start_loop(  # CSV PROCESSOR
                db_client=app.state.db_client,
                func=process_csv_file,
                path=FILES_PATH,
                extension=FilesExtensionEnum.CSV,
                db="main"
            ))

            asyncio.create_task(finder.start_loop(  # EXCEL PROCESSOR
                db_client=app.state.db_client,
                func=process_excel_file,
                path=EXCEL_FILES_PATH,
                extension=FilesExtensionEnum.EXCEL,
                db="main"
            ))

            asyncio.create_task(finder.start_loop(  # EXCEL CIRIUM PROCESSOR
                db_client=app.state.db_client,
                func=process_cirium_file,
                path=CIRIUM_FILES_PATH,
                extension=FilesExtensionEnum.CIRIUM,
                db="cirium"
            ))

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
        request.state.db = DBProxy(app.state.redis)

        response = await call_next(request)
        await request.state.db.close_all()

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

    # Custom ValidationError handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = getattr(request.state, "correlation_id", None)

        detail = [
            ErrorValidObject(field=".".join(map(str, e["loc"])), description=e["msg"])
            for e in exc.errors()
        ]

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorValidationResponse(
                correlationId=correlation_id,
                detail=detail,
            ).model_dump(mode="json")
        )

    # Custom 500 exception handler
    @app.exception_handler(Exception)
    async def custom_exception_handler(request: Request, exc: Exception):
        correlation_id = request.state.correlation_id
        logger.error(f"Unhandled error: {exc} \n CorrelationID = {correlation_id}", exc_info=True)

        detail = [DetailField(msg=f"{exc.__class__.__name__}: {str(exc)}")]

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                correlationId=correlation_id,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail,
            ).model_dump(mode="json")
        )

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutdown initiated...")
        logger.info("Closing redis connection...")
        await app.state.redis.close()
        logger.info("Closing database connection...")
        await app.state.db_client.dispose()
        logger.info("Shutdown completed. Bye!")


def _performance_log(seconds: float, name):
    if ENABLE_PERFORMANCE_LOGGER:
        if seconds < 60:
            perf_dec_logger.info(f"{name} completed in {seconds:.2f} seconds")
        elif seconds < 600:
            perf_dec_logger.warning(f"{name} completed in {seconds:.2f} seconds. Improve performance")
        else:
            perf_dec_logger.critical(f"{name} completed in {seconds:.2f} seconds. Improve performance!!")


def performance_timer(func):
    """
    A decorator for measuring function execution time.
    Supports both regular and async functions.
    """
    if inspect.iscoroutinefunction(func):
        # --- ASYNC  ---
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()

            elapsed = end - start
            _performance_log(elapsed, func.__name__)

            return result

        return wrapper

    else:
        # --- SYNC  ---
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()

            elapsed = end - start
            _performance_log(elapsed, func.__name__)

            return result

        return wrapper


__all__ = ["register_middlewares", "cache_query", "DBProxy", "performance_timer"]
