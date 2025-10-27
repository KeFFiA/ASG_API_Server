import json
from typing import Optional, List

import aiohttp

from Config import DREMIO_USER, DREMIO_HOST, DREMIO_PORT, DREMIO_PASS


class DremioClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.DREMIO_BASE = f"{DREMIO_HOST}:{DREMIO_PORT}".rstrip("/")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def authenticate(self):
        """Authorization in Dremio via /apiv2/login"""

        url = f"{self.DREMIO_BASE}/apiv2/login"
        payload = {"userName": DREMIO_USER, "password": DREMIO_PASS}
        async with self.session.post(url, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Dremio login failed: {resp.status} {text}")
            data = await resp.json()
            self.token = data.get("token")
            if not self.token:
                raise RuntimeError("No token in Dremio login response")

    def headers(self):
        if not self.token:
            raise RuntimeError("Not authenticated to Dremio")
        return {
            "Authorization": f"_dremio{self.token}",
            "Content-Type": "application/json"
        }

    async def create_virtual_dataset(
        self,
        space: str,
        view_name: str,
        sql: str,
        sql_context: Optional[List[str]] = None
    ):
        """Create a VIRTUAL DATASET (similar to Save as view)"""
        url = f"{self.DREMIO_BASE}/api/v3/catalog"
        payload = {
            "entityType": "dataset",
            "type": "VIRTUAL_DATASET",
            "path": [space, view_name],
            "sql": sql,
        }
        if sql_context:
            payload["sqlContext"] = sql_context

        async with self.session.post(
            url, json=payload, headers=self.headers(), ssl=False
        ) as resp:
            text = await resp.text()
            if resp.status not in (200, 201):
                raise RuntimeError(
                    f"Failed to create VDS ({view_name}): {resp.status} {text}"
                )
            return json.loads(text)


__all__ = ["DremioClient"]
