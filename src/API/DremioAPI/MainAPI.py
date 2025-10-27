import asyncio
from typing import List

from API.Clients import DremioClient
from Config import setup_logger

logger = setup_logger(name="dremio_api")

async def transfer_tables_to_dremio(
        *,
        tables: List[str],
        dremio_space: str,
        dremio_source_name: str,
        preserve_table_name: bool = True
):
    """Migrating tables from Postgres to Dremio (creating a VDS)"""

    await asyncio.sleep(60)

    async with DremioClient() as dremio:
        results = []
        for tbl in tables:
            if "." in tbl:
                schema, table = tbl.split(".", 1)
            else:
                schema, table = None, tbl

            if schema:
                sql_context = [dremio_source_name, schema]
                dremio_fqn = f'"{dremio_source_name}"."{schema}"."{table}"'
            else:
                sql_context = [dremio_source_name]
                dremio_fqn = f'"{dremio_source_name}"."{table}"'

            sql = f"SELECT * FROM {dremio_fqn}"
            view_name = table if preserve_table_name else f"{dremio_source_name}_{table}"

            logger.info(f"Creating VDS: {dremio_space}/{view_name}")
            vds = await dremio.create_virtual_dataset(
                space=dremio_space,
                view_name=view_name,
                sql=sql,
                sql_context=sql_context
            )

            results.append({
                "table": tbl,
                "view_name": view_name,
                "vds_id": vds.get("id"),
                "path": vds.get("path")
            })

        return results


__all__ = ["transfer_tables_to_dremio"]
