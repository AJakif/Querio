
    
    

with all_values as (

    select
        payment_type as value_field,
        count(*) as n_records

    from "querio"."marts"."fct_orders"
    group by payment_type

)

select *
from all_values
where value_field not in (
    'credit_card','boleto','debit_card','voucher'
)


