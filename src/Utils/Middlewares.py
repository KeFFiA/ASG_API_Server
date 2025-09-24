import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastapi import Request
from fastapi.responses import JSONResponse

from Config import setup_logger, DBSettings
from Database import DatabaseClient

from .FindCSV import find_csv_loop
from .FindJSON import find_json_loop

logger = setup_logger(
    'fastapi_app',
    log_format='%(levelname)s:     [%(name)s] %(asctime)s | %(message)s'
)

engine_cache = {}
session_cache = {}

class DBProxy:
    def __init__(self):
        self._open_sessions = []
        self.db_settings = DBSettings()

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

def register_middlewares(app):
    # Middleware for requests logging
    @app.middleware("http")
    async def log_and_db_requests(request: Request, call_next):
        start_time = asyncio.get_event_loop().time()
        request.state.db = DBProxy()

        try:
            response = await call_next(request)
        finally:
            await request.state.db.close_all()

        duration = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"{request.method} {request.url.path} completed_in={duration:.2f}s "
            f"status_code={response.status_code}"
        )
        return response

    # Custom exception handler
    @app.exception_handler(Exception)
    async def custom_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"},
    )

    @app.on_event("startup")
    async def startup_event():
        client = DatabaseClient()
        try:
            asyncio.create_task(find_json_loop(client))
            asyncio.create_task(find_csv_loop(client))
        finally:
            await client.dispose()