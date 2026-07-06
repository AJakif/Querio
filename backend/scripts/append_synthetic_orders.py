"""Append a fresh batch of synthetic orders to the raw schema."""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import psycopg2

from scripts import load_raw

DSN = os.environ.get("DATABASE_URL", "postgresql://querio:querio@localhost:5432/querio")
DEFAULT_BATCH_SIZE = int(os.environ.get("REFRESH_ORDER_BATCH_SIZE", "100"))
REFRESH_SEED_OFFSET = 10_000


def _fetch_id_rows(cursor, table: str, column_name: str) -> list[dict[str, str]]:
    cursor.execute(f"SELECT {column_name} FROM raw.{table} ORDER BY {column_name}")
    return [{column_name: row[0]} for row in cursor.fetchall()]


def _fetch_refresh_state(cursor) -> tuple[int, int, datetime]:
    cursor.execute(
        "SELECT order_id, order_purchase_timestamp FROM raw.orders ORDER BY order_id DESC LIMIT 1"
    )
    latest_order = cursor.fetchone()
    if latest_order is None:
        raise RuntimeError("raw.orders is empty. Run scripts/load_raw.py before refreshing.")

    cursor.execute("SELECT review_id FROM raw.order_reviews ORDER BY review_id DESC LIMIT 1")
    latest_review = cursor.fetchone()

    latest_order_number = int(latest_order[0].replace("ORD", ""))
    latest_review_number = int(latest_review[0].replace("REV", "")) if latest_review else 0
    latest_purchase_timestamp = latest_order[1]
    return latest_order_number, latest_review_number, latest_purchase_timestamp


def generate_incremental_refresh_batch(
    batch_size: int,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    sellers: list[dict[str, str]],
    starting_order_number: int,
    starting_review_number: int,
    start_purchase_timestamp: datetime,
    seed: int,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    rng = random.Random(seed)
    orders: list[dict] = []
    order_items: list[dict] = []
    order_payments: list[dict] = []
    order_reviews: list[dict] = []
    review_number = starting_review_number
    base_purchase_timestamp = start_purchase_timestamp + timedelta(hours=1)

    for offset in range(batch_size):
        order_number = starting_order_number + offset
        order_id = f"ORD{order_number:05d}"
        customer = rng.choice(customers)
        status = load_raw._weighted_choice(load_raw.ORDER_STATUSES, rng)
        purchase_ts = base_purchase_timestamp + timedelta(
            hours=offset,
            minutes=rng.randint(0, 59),
        )
        approved_ts = purchase_ts + timedelta(hours=rng.randint(1, 24))
        estimated_delivery = purchase_ts + timedelta(days=rng.randint(10, 25))

        delivered_carrier_ts = None
        delivered_customer_ts = None
        if status == "delivered":
            delivered_carrier_ts = approved_ts + timedelta(days=rng.randint(1, 5))
            delivered_customer_ts = delivered_carrier_ts + timedelta(days=rng.randint(1, 7))
        elif status == "shipped":
            delivered_carrier_ts = approved_ts + timedelta(days=rng.randint(1, 3))

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_status": status,
                "order_purchase_timestamp": purchase_ts,
                "order_approved_at": approved_ts,
                "order_delivered_carrier_date": delivered_carrier_ts,
                "order_delivered_customer_date": delivered_customer_ts,
                "order_estimated_delivery_date": estimated_delivery,
            }
        )

        item_total = 0.0
        item_count = rng.choices([1, 2, 3], weights=[70, 20, 10], k=1)[0]
        for item_index in range(1, item_count + 1):
            product = rng.choice(products)
            seller = rng.choice(sellers)
            price = round(rng.uniform(20.0, 550.0), 2)
            freight = round(rng.uniform(5.0, 45.0), 2)
            item_total += price + freight
            order_items.append(
                {
                    "order_id": order_id,
                    "order_item_id": item_index,
                    "product_id": product["product_id"],
                    "seller_id": seller["seller_id"],
                    "shipping_limit_date": purchase_ts + timedelta(days=rng.randint(2, 10)),
                    "price": price,
                    "freight_value": freight,
                }
            )

        payment_type = load_raw._weighted_choice(load_raw.PAYMENT_TYPES, rng)
        installments = rng.choices(
            [1, 2, 3, 4, 6, 8, 10],
            weights=[35, 20, 15, 10, 8, 7, 5],
            k=1,
        )[0]
        order_payments.append(
            {
                "order_id": order_id,
                "payment_sequential": 1,
                "payment_type": payment_type,
                "payment_installments": installments,
                "payment_value": round(item_total, 2),
            }
        )

        if status == "delivered":
            review_number += 1
            score = rng.choices([5, 4, 3, 2, 1], weights=[50, 23, 14, 7, 6], k=1)[0]
            review_title = rng.choice(
                {
                    5: ["Excelente!", "Entrega rapida", "Otima compra"],
                    4: ["Bom produto", "Satisfeito", "Valeu a pena"],
                    3: ["Razoavel", "Tudo certo", "Esperava mais"],
                    2: ["Atrasou", "Produto mediano", "Nao gostei muito"],
                    1: ["Pessimo", "Nao recomendo", "Veio com problema"],
                }[score]
            )
            review_created_at = delivered_customer_ts + timedelta(days=rng.randint(1, 5))
            order_reviews.append(
                {
                    "review_id": f"REV{review_number:05d}",
                    "order_id": order_id,
                    "review_score": score,
                    "review_comment_title": review_title,
                    "review_comment_message": f"Refresh review for {order_id} - {review_title}",
                    "review_creation_date": review_created_at,
                    "review_answer_timestamp": review_created_at + timedelta(days=1),
                }
            )

    return orders, order_items, order_payments, order_reviews


def main() -> None:
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            customers = _fetch_id_rows(cur, "customers", "customer_id")
            products = _fetch_id_rows(cur, "products", "product_id")
            sellers = _fetch_id_rows(cur, "sellers", "seller_id")
            latest_order_number, latest_review_number, latest_purchase_timestamp = _fetch_refresh_state(cur)

            orders, order_items, order_payments, order_reviews = generate_incremental_refresh_batch(
                batch_size=DEFAULT_BATCH_SIZE,
                customers=customers,
                products=products,
                sellers=sellers,
                starting_order_number=latest_order_number + 1,
                starting_review_number=latest_review_number,
                start_purchase_timestamp=latest_purchase_timestamp,
                seed=REFRESH_SEED_OFFSET + latest_order_number,
            )

            cur.execute(load_raw._build_insert("raw.orders", orders))
            cur.execute(load_raw._build_insert("raw.order_items", order_items))
            cur.execute(load_raw._build_insert("raw.order_payments", order_payments))
            if order_reviews:
                cur.execute(load_raw._build_insert("raw.order_reviews", order_reviews))
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
