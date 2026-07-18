"""Generate Olist data directly into the `raw` schema in Postgres.

Usage:
    python scripts/load_raw.py

Mirrors the structure of the real Olist Brazilian E-Commerce CSVs but
generates deterministic, arithmetically coherent sample data so the
dbt pipeline has something real to transform.

The `raw` schema tables match the original Olist CSV names exactly
(without the `olist_` prefix used by the public dataset files).
"""

import os
import random
from datetime import datetime, timedelta

import psycopg2

DSN = os.environ.get("DATABASE_URL", "postgresql://querio:querio@localhost:5432/querio")

SEED = 42


def seed_database_enabled() -> bool:
    """Return whether the bundled deterministic demo dataset should be loaded."""
    return os.environ.get("SEED_DATABASE", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }

BRAZILIAN_STATES = [
    ("SP", "São Paulo"), ("RJ", "Rio de Janeiro"), ("MG", "Minas Gerais"),
    ("RS", "Rio Grande do Sul"), ("PR", "Paraná"), ("BA", "Bahia"),
    ("SC", "Santa Catarina"), ("PE", "Pernambuco"), ("CE", "Ceará"),
    ("PA", "Pará"), ("MA", "Maranhão"), ("GO", "Goiás"),
    ("ES", "Espírito Santo"), ("DF", "Distrito Federal"), ("AM", "Amazonas"),
]

BRAZILIAN_CITIES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Porto Alegre", "RS"), ("Curitiba", "PR"), ("Salvador", "BA"),
    ("Florianópolis", "SC"), ("Recife", "PE"), ("Fortaleza", "CE"),
    ("Belém", "PA"), ("São Luís", "MA"), ("Goiânia", "GO"),
    ("Vitória", "ES"), ("Brasília", "DF"), ("Manaus", "AM"),
    ("Campinas", "SP"), ("Santos", "SP"), ("São José dos Campos", "SP"),
    ("Ribeirão Preto", "SP"), ("Niterói", "RJ"),
]

PRODUCT_CATEGORIES = [
    ("beleza_saude", "health_beauty"),
    ("esporte_lazer", "sports_leisure"),
    ("moveis_decoracao", "furniture_decor"),
    ("informatica_acessorios", "computers_accessories"),
    ("utilidades_domesticas", "household_utilities"),
    ("relogios_presentes", "watches_gifts"),
    ("telefonia", "telephony"),
    ("brinquedos", "toys"),
    ("cama_mesa_banho", "bed_bath_table"),
    ("eletronicos", "electronics"),
    ("ferramentas_jardim", "tools_garden"),
    ("automotivo", "automotive"),
    ("alimentos_bebidas", "food_drinks"),
    ("livros_interesse", "books_general"),
    ("papelaria", "stationery"),
    ("eletrodomesticos", "appliances"),
    ("moda_vestuario", "fashion_clothing"),
    ("bebes", "baby"),
    ("musica", "music"),
    ("filmes_series", "movies_series"),
    ("consoles_games", "consoles_games"),
    ("pet_shop", "pet_shop"),
    ("artes", "arts"),
    ("construcao_ferramentas", "construction_tools"),
    ("casa_conforto", "home_comfort"),
    ("malas_acessorios", "luggage_accessories"),
    ("moveis_escritorio", "office_furniture"),
    ("portateis", "portable_tech"),
    ("instrumentos_musicais", "musical_instruments"),
    ("parceiros", "partners"),
]

ORDER_STATUSES = [
    ("delivered", 0.955),
    ("shipped", 0.020),
    ("processing", 0.015),
    ("canceled", 0.008),
    ("invoiced", 0.002),
]

PAYMENT_TYPES = [
    ("credit_card", 0.74),
    ("boleto", 0.18),
    ("debit_card", 0.05),
    ("voucher", 0.03),
]

PRODUCT_NAMES: dict[str, tuple[str, int, int, int, float, float, float, float]] = {
    "beleza_saude": ("Perfume Importado", 30, 200, 3, 200, 12, 8, 5),
    "esporte_lazer": ("Bicicleta Aço", 45, 500, 5, 12000, 150, 80, 30),
    "moveis_decoracao": ("Sofá 3 Lugares", 25, 600, 4, 25000, 200, 85, 90),
    "informatica_acessorios": ("Mouse Wireless", 20, 100, 2, 150, 15, 5, 8),
    "utilidades_domesticas": ("Aspirador Pó", 28, 250, 3, 3500, 35, 25, 20),
    "relogios_presentes": ("Relógio Cronógrafo", 22, 150, 3, 80, 25, 5, 4),
    "telefonia": ("Smartphone Android", 35, 400, 4, 180, 16, 8, 1),
    "brinquedos": ("Boneca Educativa", 18, 120, 3, 350, 30, 20, 15),
    "cama_mesa_banho": ("Kit Toalhas 4 Peças", 15, 80, 2, 800, 50, 30, 5),
    "eletronicos": ("Fone Ouvido Bluetooth", 25, 180, 3, 120, 18, 10, 5),
    "ferramentas_jardim": ("Kit Jardim 12 Peças", 30, 200, 4, 1500, 40, 25, 20),
    "automotivo": ("Câmera Ré", 22, 150, 3, 400, 10, 6, 8),
    "alimentos_bebidas": ("Café Gourmet 1kg", 10, 50, 1, 1000, 20, 15, 10),
    "livros_interesse": ("Livro Best-Seller", 15, 350, 1, 400, 22, 15, 3),
    "papelaria": ("Caneta Tinteiro", 12, 60, 2, 50, 15, 2, 2),
    "eletrodomesticos": ("Geladeira Frost Free", 40, 800, 5, 35000, 180, 90, 70),
    "moda_vestuario": ("Vestido Floral", 20, 150, 3, 250, 60, 40, 2),
    "bebes": ("Cadeirinha Carro", 28, 200, 4, 5000, 45, 35, 30),
    "musica": ("Violão Acústico", 35, 300, 3, 2500, 100, 15, 40),
    "filmes_series": ("Box DVD Coleção", 18, 100, 2, 300, 20, 15, 3),
    "consoles_games": ("Console Videogame", 25, 450, 4, 2500, 30, 20, 10),
    "pet_shop": ("Ração Premium 15kg", 15, 80, 1, 15000, 40, 30, 10),
    "artes": ("Tela Pintura Decorativa", 20, 150, 2, 800, 60, 40, 5),
    "construcao_ferramentas": ("Furadeira Impacto", 25, 200, 3, 3000, 35, 25, 18),
    "casa_conforto": ("Tapete Sala 3m", 15, 120, 2, 4500, 180, 5, 80),
    "malas_acessorios": ("Mala Viagem Bordo", 18, 180, 3, 2000, 55, 35, 22),
    "moveis_escritorio": ("Cadeira Ergonômica", 30, 400, 4, 12000, 110, 55, 60),
    "portateis": ("Notebook Ultrafino", 38, 600, 4, 1800, 32, 2, 25),
    "instrumentos_musicais": ("Teclado 61 Teclas", 35, 350, 3, 5500, 95, 12, 35),
    "parceiros": ("Kit Ferramentas 100", 28, 300, 4, 8000, 55, 40, 25),
}

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elena", "Fernando", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Lucas", "Marina", "Nelson", "Olívia", "Paulo",
    "Renata", "Sérgio", "Tatiana", "Ubirajara", "Valéria", "Wagner", "Xavier", "Yara",
    "Zé", "Aline", "Bernardo", "Camila", "Daniel", "Elisa",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Pereira", "Almeida",
    "Nascimento", "Araújo", "Barbosa", "Ribeiro", "Carvalho", "Gomes", "Martins",
    "Rodrigues", "Alves", "Moreira", "Ferreira", "Dias",
]

ZIP_CODES_BY_STATE: dict[str, str] = {
    "SP": "01000", "RJ": "20000", "MG": "30000", "RS": "90000",
    "PR": "80000", "BA": "40000", "SC": "88000", "PE": "50000",
    "CE": "60000", "PA": "66000", "MA": "65000", "GO": "74000",
    "ES": "29000", "DF": "70000", "AM": "69000",
}

RAW_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;

DROP TABLE IF EXISTS raw.order_reviews CASCADE;
DROP TABLE IF EXISTS raw.order_payments CASCADE;
DROP TABLE IF EXISTS raw.order_items CASCADE;
DROP TABLE IF EXISTS raw.orders CASCADE;
DROP TABLE IF EXISTS raw.customers CASCADE;
DROP TABLE IF EXISTS raw.products CASCADE;
DROP TABLE IF EXISTS raw.sellers CASCADE;
DROP TABLE IF EXISTS raw.geolocation CASCADE;
DROP TABLE IF EXISTS raw.product_category_name_translation CASCADE;

CREATE TABLE raw.customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state VARCHAR(2)
);

CREATE TABLE raw.geolocation (
    geolocation_zip_code_prefix VARCHAR(10),
    geolocation_lat NUMERIC(10,6),
    geolocation_lng NUMERIC(10,6),
    geolocation_city VARCHAR(100),
    geolocation_state VARCHAR(2)
);

CREATE TABLE raw.products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10,2),
    product_length_cm NUMERIC(10,2),
    product_height_cm NUMERIC(10,2),
    product_width_cm NUMERIC(10,2)
);

CREATE TABLE raw.sellers (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(100),
    seller_state VARCHAR(2)
);

CREATE TABLE raw.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    order_status VARCHAR(20),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES raw.customers(customer_id)
);

CREATE TABLE raw.order_items (
    order_id VARCHAR(50) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2),
    freight_value NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES raw.orders(order_id),
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES raw.products(product_id),
    CONSTRAINT fk_order_items_seller
        FOREIGN KEY (seller_id) REFERENCES raw.sellers(seller_id)
);

CREATE TABLE raw.order_payments (
    order_id VARCHAR(50) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(20),
    payment_installments INTEGER,
    payment_value NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_order_payments_order
        FOREIGN KEY (order_id) REFERENCES raw.orders(order_id)
);

CREATE TABLE raw.order_reviews (
    review_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    review_score INTEGER,
    review_comment_title VARCHAR(200),
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    CONSTRAINT fk_order_reviews_order
        FOREIGN KEY (order_id) REFERENCES raw.orders(order_id)
);

CREATE TABLE raw.product_category_name_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);
"""


def _weighted_choice(options: list[tuple[str, float]], rng: random.Random) -> str:
    values, weights = zip(*options)
    return rng.choices(values, weights=weights, k=1)[0]


def _generate_customers(rng: random.Random, count: int) -> list[dict]:
    customers = []
    for i in range(1, count + 1):
        cid = f"CUST{i:05d}"
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        state, _ = rng.choice(BRAZILIAN_STATES)
        city = rng.choice([c for c, s in BRAZILIAN_CITIES if s == state] or ["São Paulo"])
        zip_prefix = f"{rng.randint(1000, 9999)}"
        customers.append({
            "customer_id": cid,
            "customer_unique_id": f"UNIQ{cid}",
            "customer_zip_code_prefix": zip_prefix,
            "customer_city": city,
            "customer_state": state,
        })
    return customers


def _generate_sellers(rng: random.Random, count: int) -> list[dict]:
    sellers = []
    for i in range(1, count + 1):
        sid = f"SELL{i:05d}"
        state, _ = rng.choice(BRAZILIAN_STATES)
        city = rng.choice([c for c, s in BRAZILIAN_CITIES if s == state] or ["São Paulo"])
        sellers.append({
            "seller_id": sid,
            "seller_zip_code_prefix": f"{rng.randint(1000, 9999)}",
            "seller_city": city,
            "seller_state": state,
        })
    return sellers


def _generate_products(rng: random.Random) -> list[dict]:
    products = []
    cat_keys = list(PRODUCT_NAMES.keys())
    for i, cat in enumerate(cat_keys):
        for j in range(1, 3):
            pid = f"PROD{i+1:02d}{j:02d}"
            name, nl, dl, pq, wg, lc, hc, wc = PRODUCT_NAMES[cat]
            variance = rng.uniform(0.8, 1.2)
            products.append({
                "product_id": pid,
                "product_category_name": cat,
                "product_name_lenght": int(nl * variance),
                "product_description_lenght": int(dl * variance),
                "product_photos_qty": max(1, int(pq * variance)),
                "product_weight_g": round(wg * variance, 2),
                "product_length_cm": round(lc * variance, 2),
                "product_height_cm": round(hc * variance, 2),
                "product_width_cm": round(wc * variance, 2),
            })
    return products


def _generate_orders(
    rng: random.Random,
    count: int,
    customers: list[dict],
    products: list[dict],
    sellers: list[dict],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    orders = []
    all_items = []
    all_payments = []
    all_reviews = []

    base_date = datetime(2024, 1, 1)

    for i in range(1, count + 1):
        oid = f"ORD{i:05d}"
        customer = rng.choice(customers)
        status = _weighted_choice(ORDER_STATUSES, rng)

        purchase_ts = base_date + timedelta(
            days=rng.randint(0, 545),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )
        approved_ts = purchase_ts + timedelta(hours=rng.randint(1, 48))
        estimated_delivery = purchase_ts + timedelta(days=rng.randint(15, 40))

        delivered_carrier_ts = None
        delivered_customer_ts = None
        if status == "delivered":
            delivered_carrier_ts = approved_ts + timedelta(days=rng.randint(1, 10))
            delivered_customer_ts = delivered_carrier_ts + timedelta(days=rng.randint(1, 15))
        elif status == "shipped":
            delivered_carrier_ts = approved_ts + timedelta(days=rng.randint(1, 5))

        orders.append({
            "order_id": oid,
            "customer_id": customer["customer_id"],
            "order_status": status,
            "order_purchase_timestamp": purchase_ts,
            "order_approved_at": approved_ts,
            "order_delivered_carrier_date": delivered_carrier_ts,
            "order_delivered_customer_date": delivered_customer_ts,
            "order_estimated_delivery_date": estimated_delivery,
        })

        num_items = rng.choices([1, 2, 3, 4, 5], weights=[60, 25, 10, 3, 2], k=1)[0]
        item_total = 0.0

        for item_idx in range(1, num_items + 1):
            product = rng.choice(products)
            seller = rng.choice(sellers)
            price = round(rng.uniform(15.0, 500.0), 2)
            freight = round(rng.uniform(5.0, 50.0), 2)
            item_total += price + freight
            shipping_limit = purchase_ts + timedelta(days=rng.randint(3, 15))

            all_items.append({
                "order_id": oid,
                "order_item_id": item_idx,
                "product_id": product["product_id"],
                "seller_id": seller["seller_id"],
                "shipping_limit_date": shipping_limit,
                "price": price,
                "freight_value": freight,
            })

        payment_type = _weighted_choice(PAYMENT_TYPES, rng)
        installments = rng.choices(
            [1, 2, 3, 4, 5, 6, 8, 10, 12],
            weights=[30, 20, 15, 10, 8, 5, 5, 4, 3], k=1,
        )[0]
        all_payments.append({
            "order_id": oid,
            "payment_sequential": 1,
            "payment_type": payment_type,
            "payment_installments": installments,
            "payment_value": round(item_total, 2),
        })

        if status == "delivered":
            rid = f"REV{i:05d}"
            score = rng.choices([5, 4, 3, 2, 1], weights=[45, 25, 15, 8, 7], k=1)[0]
            review_titles = {
                5: ["Excelente!", "Muito bom", "Recomendo!", "Produto incrível"],
                4: ["Bom produto", "Satisfeito", "Atendeu expectativas"],
                3: ["Razoável", "Mais ou menos", "Poderia ser melhor"],
                2: ["Decepcionante", "Não gostei", "Abaixo do esperado"],
                1: ["Péssimo!", "Horrível", "Não recomendo"],
            }
            title = rng.choice(review_titles[score])
            review_ts = delivered_customer_ts + timedelta(days=rng.randint(1, 10))
            all_reviews.append({
                "review_id": rid,
                "order_id": oid,
                "review_score": score,
                "review_comment_title": title,
                "review_comment_message": f"Review for order {oid} - {title}",
                "review_creation_date": review_ts,
                "review_answer_timestamp": review_ts + timedelta(days=rng.randint(1, 3)),
            })

    return orders, all_items, all_payments, all_reviews


def _generate_geolocation(rng: random.Random) -> list[dict]:
    locs = set()
    geos = []
    for _ in range(200):
        state, _ = rng.choice(BRAZILIAN_STATES)
        city = rng.choice([c for c, s in BRAZILIAN_CITIES if s == state] or ["São Paulo"])
        zip_prefix = f"{rng.randint(1000, 9999)}"
        key = (zip_prefix, city, state)
        if key not in locs:
            locs.add(key)
            lat = round(rng.uniform(-33.0, -5.0), 6)
            lng = round(rng.uniform(-73.0, -34.0), 6)
            geos.append({
                "geolocation_zip_code_prefix": zip_prefix,
                "geolocation_lat": lat,
                "geolocation_lng": lng,
                "geolocation_city": city,
                "geolocation_state": state,
            })
    return geos


def _generate_categories(rng: random.Random) -> list[dict]:
    return [
        {"product_category_name": pt, "product_category_name_english": en}
        for pt, en in PRODUCT_CATEGORIES
    ]


def _escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(val, datetime):
        return f"'{val.isoformat()}'"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _build_insert(table: str, rows: list[dict]) -> str:
    if not rows:
        return ""
    keys = list(rows[0].keys())
    cols = ", ".join(keys)
    values = []
    for row in rows:
        vals = ", ".join(_escape(row[k]) for k in keys)
        values.append(f"({vals})")
    return f"INSERT INTO {table} ({cols}) VALUES\n" + ",\n".join(values) + ";"


def main():
    if not seed_database_enabled():
        print("SEED_DATABASE is disabled; skipping demo database seed.")
        return

    rng = random.Random(SEED)

    print("Generating data...")
    customers = _generate_customers(rng, 1000)
    sellers = _generate_sellers(rng, 50)
    products = _generate_products(rng)
    geolocation = _generate_geolocation(rng)
    categories = _generate_categories(rng)
    orders, order_items, order_payments, order_reviews = _generate_orders(
        rng, 5000, customers, products, sellers,
    )

    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            print("Creating raw schema...")
            cur.execute(RAW_SCHEMA_SQL)

            print("Seeding raw.customers...")
            cur.execute(_build_insert("raw.customers", customers))

            print("Seeding raw.geolocation...")
            cur.execute(_build_insert("raw.geolocation", geolocation))

            print("Seeding raw.products...")
            cur.execute(_build_insert("raw.products", products))

            print("Seeding raw.sellers...")
            cur.execute(_build_insert("raw.sellers", sellers))

            print("Seeding raw.orders...")
            cur.execute(_build_insert("raw.orders", orders))

            print("Seeding raw.order_items...")
            for batch_start in range(0, len(order_items), 500):
                batch = order_items[batch_start:batch_start + 500]
                cur.execute(_build_insert("raw.order_items", batch))

            print("Seeding raw.order_payments...")
            cur.execute(_build_insert("raw.order_payments", order_payments))

            print("Seeding raw.order_reviews...")
            for batch_start in range(0, len(order_reviews), 500):
                batch = order_reviews[batch_start:batch_start + 500]
                cur.execute(_build_insert("raw.order_reviews", batch))

            print("Seeding raw.product_category_name_translation...")
            cur.execute(_build_insert("raw.product_category_name_translation", categories))

        conn.commit()

        total_rows = (
            len(customers) + len(geolocation) + len(products) + len(sellers)
            + len(orders) + len(order_items) + len(order_payments) + len(order_reviews)
            + len(categories)
        )
        print(f"Raw schema seeded successfully: {total_rows} rows across 9 tables")
        print(f"  customers:                        {len(customers)}")
        print(f"  geolocation:                      {len(geolocation)}")
        print(f"  products:                         {len(products)}")
        print(f"  sellers:                          {len(sellers)}")
        print(f"  orders:                           {len(orders)}")
        print(f"  order_items:                      {len(order_items)}")
        print(f"  order_payments:                   {len(order_payments)}")
        print(f"  order_reviews:                    {len(order_reviews)}")
        print(f"  product_category_name_translation: {len(categories)}")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
