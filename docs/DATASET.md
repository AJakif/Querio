# Dataset

## Olist Brazilian E-Commerce

Querio uses the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — ~100k orders across orders, order items, products, customers, sellers, payments, and reviews.

The dataset was chosen because it has real relational structure (the agent has to reason across joins, not just filter one flat table) and sits comfortably in the 100k–1M row performance target.

The project works with deterministic synthetic data that mirrors the Olist schema exactly. The download script (`scripts/download_olist.py`) is available if you want the real CSVs.

## Data pipeline

```
raw (seed script)  ──▶  dbt run  ──▶  marts (agent queries this layer)
```

The project uses a two-layer data architecture:

- **`raw` schema** (9 tables): mirrors the original Olist CSV structure. Populated by `python scripts/load_raw.py` with deterministic, arithmetically coherent sample data (~9,500 rows).
- **`marts` schema** (2 models): analytical tables produced by dbt. The agent introspects this schema to generate queries.

## Raw schema tables

| Table | Rows | Description |
|---|---|---|
| `raw.customers` | 1,000 | Brazilian e-commerce customers with state/city |
| `raw.orders` | 5,000 | Orders with status, timestamps |
| `raw.order_items` | ~5,500 | Line items per order |
| `raw.order_payments` | 5,000 | Payment method/installments |
| `raw.order_reviews` | ~4,775 | Review scores and comments |
| `raw.products` | 60 | Products across 30 categories |
| `raw.sellers` | 50 | Sellers across Brazilian states |
| `raw.geolocation` | ~200 | Zip-code-level lat/lng data |
| `raw.product_category_name_translation` | 30 | Portuguese-to-English category name translation |

## Marts models (dbt output)

| Model | Type | Description |
|---|---|---|
| `marts.fct_orders` | Fact table | Order-level: joins orders + items + payments. One row per order with aggregated item/payment metrics. |
| `marts.dim_customers` | Dimension | Customer details with lifetime order aggregates (total orders, total spent, avg order value, first/last order date). |

## Re-seeding

```bash
# Full reset: reload raw data and rebuild dbt models
python scripts/load_raw.py
cd dbt && dbt run
```

The seed script uses a fixed random seed (`SEED = 42`), so every run produces identical results. This guarantees reproducible data for development, testing, and demo purposes.

## Scheduled refresh with Airflow

The `scheduled_data_refresh` DAG runs hourly and uses `python scripts/append_synthetic_orders.py` to append new synthetic orders into the raw schema instead of replaying the same seed from scratch. It then runs `dbt run` so the `marts` schema reflects the added rows.

- Open `http://localhost:8081` to inspect the Airflow UI.
- Trigger `scheduled_data_refresh` manually or wait for the next schedule.
- Confirm run history and task logs in Airflow after each refresh.
- Ask a freshness-sensitive question after the run to verify the rebuilt marts tables reflect the new orders.
