from app.repositories.base import SchemaRepository, ColumnInfo, RelationshipInfo


class InMemorySchemaRepository(SchemaRepository):
    def __init__(self):
        self._tables: dict[str, list[ColumnInfo]] = {
            "customers": [
                ColumnInfo("customer_id", "character varying", False),
                ColumnInfo("customer_unique_id", "character varying", False),
                ColumnInfo("customer_zip_code_prefix", "character varying", True),
                ColumnInfo("customer_city", "character varying", True),
                ColumnInfo("customer_state", "character varying", True),
            ],
            "geolocation": [
                ColumnInfo("geolocation_zip_code_prefix", "character varying", True),
                ColumnInfo("geolocation_lat", "numeric", True),
                ColumnInfo("geolocation_lng", "numeric", True),
                ColumnInfo("geolocation_city", "character varying", True),
                ColumnInfo("geolocation_state", "character varying", True),
            ],
            "products": [
                ColumnInfo("product_id", "character varying", False),
                ColumnInfo("product_category_name", "character varying", True),
                ColumnInfo("product_name_lenght", "integer", True),
                ColumnInfo("product_description_lenght", "integer", True),
                ColumnInfo("product_photos_qty", "integer", True),
                ColumnInfo("product_weight_g", "numeric", True),
                ColumnInfo("product_length_cm", "numeric", True),
                ColumnInfo("product_height_cm", "numeric", True),
                ColumnInfo("product_width_cm", "numeric", True),
            ],
            "sellers": [
                ColumnInfo("seller_id", "character varying", False),
                ColumnInfo("seller_zip_code_prefix", "character varying", True),
                ColumnInfo("seller_city", "character varying", True),
                ColumnInfo("seller_state", "character varying", True),
            ],
            "orders": [
                ColumnInfo("order_id", "character varying", False),
                ColumnInfo("customer_id", "character varying", False),
                ColumnInfo("order_status", "character varying", True),
                ColumnInfo("order_purchase_timestamp", "timestamp without time zone", True),
                ColumnInfo("order_approved_at", "timestamp without time zone", True),
                ColumnInfo("order_delivered_carrier_date", "timestamp without time zone", True),
                ColumnInfo("order_delivered_customer_date", "timestamp without time zone", True),
                ColumnInfo("order_estimated_delivery_date", "timestamp without time zone", True),
            ],
            "order_items": [
                ColumnInfo("order_id", "character varying", False),
                ColumnInfo("order_item_id", "integer", False),
                ColumnInfo("product_id", "character varying", False),
                ColumnInfo("seller_id", "character varying", False),
                ColumnInfo("shipping_limit_date", "timestamp without time zone", True),
                ColumnInfo("price", "numeric", True),
                ColumnInfo("freight_value", "numeric", True),
            ],
            "order_payments": [
                ColumnInfo("order_id", "character varying", False),
                ColumnInfo("payment_sequential", "integer", False),
                ColumnInfo("payment_type", "character varying", True),
                ColumnInfo("payment_installments", "integer", True),
                ColumnInfo("payment_value", "numeric", True),
            ],
            "order_reviews": [
                ColumnInfo("review_id", "character varying", False),
                ColumnInfo("order_id", "character varying", False),
                ColumnInfo("review_score", "integer", True),
                ColumnInfo("review_comment_title", "character varying", True),
                ColumnInfo("review_comment_message", "text", True),
                ColumnInfo("review_creation_date", "timestamp without time zone", True),
                ColumnInfo("review_answer_timestamp", "timestamp without time zone", True),
            ],
            "product_categories": [
                ColumnInfo("product_category_name", "character varying", False),
                ColumnInfo("product_category_name_english", "character varying", True),
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
            RelationshipInfo(
                source_table="order_items", source_column="order_id",
                target_table="orders", target_column="order_id",
            ),
            RelationshipInfo(
                source_table="order_items", source_column="product_id",
                target_table="products", target_column="product_id",
            ),
            RelationshipInfo(
                source_table="order_items", source_column="seller_id",
                target_table="sellers", target_column="seller_id",
            ),
            RelationshipInfo(
                source_table="order_payments", source_column="order_id",
                target_table="orders", target_column="order_id",
            ),
            RelationshipInfo(
                source_table="order_reviews", source_column="order_id",
                target_table="orders", target_column="order_id",
            ),
        ]
