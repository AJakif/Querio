from app.repositories.base import SchemaRepository, ColumnInfo, RelationshipInfo


class InMemorySchemaRepository(SchemaRepository):
    def __init__(self):
        self._tables: dict[str, list[ColumnInfo]] = {
            "orders": [
                ColumnInfo("order_id", "integer", False),
                ColumnInfo("customer_id", "integer", False),
                ColumnInfo("order_date", "timestamp", False),
                ColumnInfo("total", "numeric", True),
            ],
            "customers": [
                ColumnInfo("customer_id", "integer", False),
                ColumnInfo("name", "varchar", False),
                ColumnInfo("email", "varchar", True),
            ],
        }

    async def get_tables(self) -> list[str]:
        return list(self._tables.keys())

    async def get_columns(self, table: str) -> list[ColumnInfo]:
        return self._tables.get(table, [])

    async def get_relationships(self) -> list[RelationshipInfo]:
        return [
            RelationshipInfo(
                source_table="orders", source_column="customer_id",
                target_table="customers", target_column="customer_id",
            ),
        ]
