import asyncio
from typing import List

from sqlalchemy import select

from API.Clients import DremioClient
from Config import setup_logger
from Database import DatabaseClient, DremioViews

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

    client: DatabaseClient = DatabaseClient()
    async with DremioClient() as dremio:
        results = []
        async with client.session("service") as session:
            result = await session.execute(select(DremioViews))
            rows: List[DremioViews] = result.scalars().all()
            rows_list = [(row.table_name, row.vds_id) for row in rows]
            if rows_list:
                _tables, _ids = zip(*rows_list)
            else:
                _tables, _ids = [], []

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

            if table in _tables:
                logger.info(f"Updating VDS: {dremio_space}/{view_name}")
                vds = await dremio.update_virtual_dataset(
                    dataset_id=_ids[_tables.index(table)],
                    space=dremio_space,
                    view_name=view_name,
                    sql=sql,
                    sql_context=sql_context
                )
            else:
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

            async with client.session("service") as session:
                if table not in _tables:
                    row = DremioViews(
                        vds_id=vds.get("id"),
                        view_name=view_name,
                        path=vds.get("path"),
                        table_name=vds.get("path")[-1]
                    )
                    session.add(row)
        return results


__all__ = ["transfer_tables_to_dremio"]
