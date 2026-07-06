
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

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



  
  
      
    ) dbt_internal_test