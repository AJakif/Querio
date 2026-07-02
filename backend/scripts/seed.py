"""Seed the database with a minimal set of tables and sample data."""

import os
import psycopg2

DSN = os.environ.get("DATABASE_URL", "postgresql://querio:querio@localhost:5432/querio")

SCHEMA_SQL = """
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    total NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""

DATA_SQL = """
INSERT INTO customers (name, email, city, state) VALUES
    ('Alice Silva', 'alice@example.com', 'Sao Paulo', 'SP'),
    ('Bruno Costa', 'bruno@example.com', 'Rio de Janeiro', 'RJ'),
    ('Carla Oliveira', 'carla@example.com', 'Belo Horizonte', 'MG'),
    ('Diego Santos', 'diego@example.com', 'Curitiba', 'PR'),
    ('Elena Souza', 'elena@example.com', 'Porto Alegre', 'RS');

INSERT INTO orders (customer_id, total, status, created_at) VALUES
    (1, 150.00, 'delivered', '2024-01-15'),
    (2, 250.00, 'delivered', '2024-02-20'),
    (1,  99.99, 'processing', '2024-03-10'),
    (3, 500.00, 'delivered', '2024-03-15'),
    (2,  75.50, 'shipped', '2024-04-01'),
    (4, 200.00, 'delivered', '2024-04-10'),
    (5, 320.00, 'processing', '2024-05-05'),
    (3, 180.00, 'shipped', '2024-05-20'),
    (1,  50.00, 'canceled', '2024-06-01'),
    (4, 410.00, 'delivered', '2024-06-15');
"""


def main():
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(DATA_SQL)
        conn.commit()
        print("Database seeded: customers (5 rows), orders (10 rows)")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
