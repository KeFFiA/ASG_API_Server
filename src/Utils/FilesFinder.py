import asyncio
import os
from glob import glob
from pathlib import Path
from typing import Callable, Awaitable

from Config import setup_logger
from Database import DatabaseClient
from Schemas.Enums.service import FilesExtensionEnum

logger = setup_logger(name="file_finder")


class Finder:
    def __init__(self):
        self.count: int = 0
        self.files: list[str] | None = None
        logger.debug("Initialized finder(-s)")

    async def find(self, path: Path, extension: str) -> tuple[list[str], int]:
        self.files = sorted(glob(os.path.join(path, f"*.{extension}")),
                            key=os.path.getmtime)
        self.count = len(self.files)
        logger.debug(f"[{extension.upper()}] Found {self.count} files")

        return self.files, self.count

    async def start_loop(self,
                         *,
                         path: Path,
                         extension: FilesExtensionEnum,
                         db_client: DatabaseClient,
                         db_table: str,
                         func: Callable[..., Awaitable[None]],
                         **kwargs
                         ):
        while True:
            async with db_client.session(db_table) as session:
                _files, _count = await self.find(path=path, extension=extension.value)
                if _count > 0:
                    for _file in _files:
                        logger.debug(f"[{extension.value.upper()}] Sending '{_file.split('\\')[-1]}' to {func.__name__} function")
                        await func(session, _file, **kwargs)

            logger.debug(f"[{extension.value.upper()}] Waiting for new files...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    print(sorted(glob(os.path.join(path, f"*.{extension}")),
                            key=os.path.getmtime))
