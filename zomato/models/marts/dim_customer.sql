select 
customer_id,
customer_name,
email,
age,
CASE WHEN age < 25 then 'GenZ'
    WHEN age < 40 then 'Millennial'
    WHEN age < 60 then 'GenX'
    WHEN age is null then 'unknown'
    ELSE 'Boomer' END as age_group,
gender,
marital_status,
occupation,
education,
family_size,
income_band
from {{ ref('stg_users') }}