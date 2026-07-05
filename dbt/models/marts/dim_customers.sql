with customers as (
    select * from {{ source('raw', 'customers') }}
),

fct_orders as (
    select * from {{ ref('fct_orders') }}
),

customer_orders as (
    select
        customer_id,
        count(*) as total_orders,
        sum(total_payment_value) as total_spent,
        avg(total_payment_value) as avg_order_value,
        min(order_purchase_timestamp) as first_order_date,
        max(order_purchase_timestamp) as last_order_date
    from fct_orders
    group by customer_id
)

select
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    coalesce(co.total_orders, 0) as total_orders,
    coalesce(co.total_spent, 0) as total_spent,
    coalesce(co.avg_order_value, 0) as avg_order_value,
    co.first_order_date,
    co.last_order_date
from customers c
left join customer_orders co on c.customer_id = co.customer_id
