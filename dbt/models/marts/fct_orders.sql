with orders as (
    select * from {{ source('raw', 'orders') }}
),

order_items as (
    select * from {{ source('raw', 'order_items') }}
),

order_payments as (
    select
        order_id,
        payment_type,
        payment_installments,
        payment_value
    from (
        select
            *,
            row_number() over (
                partition by order_id
                order by payment_sequential
            ) as rn
        from {{ source('raw', 'order_payments') }}
    ) ranked
    where rn = 1
),

item_aggregates as (
    select
        order_id,
        count(*) as total_items,
        sum(price) + sum(freight_value) as total_item_value
    from order_items
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    o.order_status,
    coalesce(ia.total_items, 0) as total_items,
    coalesce(ia.total_item_value, 0) as total_item_value,
    coalesce(op.payment_value, 0) as total_payment_value,
    op.payment_type,
    op.payment_installments,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date
from orders o
left join item_aggregates ia on o.order_id = ia.order_id
left join order_payments op on o.order_id = op.order_id
