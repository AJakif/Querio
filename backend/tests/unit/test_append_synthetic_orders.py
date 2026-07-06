from datetime import datetime

from scripts.append_synthetic_orders import generate_incremental_refresh_batch


def test_incremental_refresh_batch_creates_new_order_ids_and_future_timestamps():
    customers = [{"customer_id": "CUST00001"}]
    products = [{"product_id": "PROD0101"}]
    sellers = [{"seller_id": "SELL00001"}]

    orders, items, payments, reviews = generate_incremental_refresh_batch(
        batch_size=3,
        customers=customers,
        products=products,
        sellers=sellers,
        starting_order_number=5001,
        starting_review_number=4901,
        start_purchase_timestamp=datetime(2025, 7, 1, 8, 0, 0),
        seed=77,
    )

    assert [order["order_id"] for order in orders] == ["ORD05001", "ORD05002", "ORD05003"]
    assert all(
        order["order_purchase_timestamp"] > datetime(2025, 7, 1, 8, 0, 0)
        for order in orders
    )
    assert {item["order_id"] for item in items}.issubset({order["order_id"] for order in orders})
    assert {payment["order_id"] for payment in payments} == {order["order_id"] for order in orders}
    assert all(review["review_id"].startswith("REV0") for review in reviews)
