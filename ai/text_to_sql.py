import os
import re
import json

import pandas as pd
import streamlit as st
import snowflake.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
MODEL = "gpt-4o-mini"

FORBIDDEN_WORDS = [
    "drop", "delete", "truncate", "alter", "update",
    "insert", "create", "replace", "grant", "revoke",
]

# Compile a regex that matches forbidden words only at word boundaries,
# so legitimate column names like "created_at" or "is_delivered" are not blocked.
_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(FORBIDDEN_WORDS) + r")\b", re.IGNORECASE
)

EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first",
    "Cancel rate by payment method",
]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Schema prompt (must mirror actual Snowflake table/column names) ──────────
SCHEMA = """
Tables available (Snowflake). Use bare table names, no database or schema prefix.

FCT_ORDERS(order_id, order_timestamp, order_date, customer_id, restaurant_id,
           city, cuisine, payment_method, order_status, is_delivered,
           items_count, sales_qty, subtotal, discount, delivery_fee, gst,
           sales_amount, customer_rating, delivery_time_min)
DIM_RESTAURANTS(restaurant_id, restaurant_name, city, cuisine, rating,
                rating_count, cost_for_two)
DIM_CUSTOMER(customer_id, customer_name, email, age, age_group, gender,
             marital_status, occupation, education, family_size, income_band)
MART_DAILY_CITY_REVENUNE(order_date, city, orders, delivered_orders,
                         cancel_rate, gmv, aov)
MART_RESTAURANTS_PERFORMANCE(restaurant_id, restaurant_name, city, cuisine,
                             orders, revenue, avg_customer_rating,
                             avg_delivery_min)
MART_DELIVERY_SAL(city, order_hour, delivered_orders, p50, p90)

Note: gmv means delivered revenue. Prefer the MART_ tables when they fit the question.
"""

SYSTEM_PROMPT = f"""
You are a Snowflake SQL expert. Write ONE SELECT query that answers the question.

Rules:
- SELECT queries only, never modify data.
- Use bare table names (FCT_ORDERS, not ZOMATO.MARTS.FCT_ORDERS).
- Add a LIMIT of 100 or less, unless the question asks for a single total.
- Reply as JSON in this exact format: {{"sql": "your query here"}}

{SCHEMA}
"""


# ── Data layer ───────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    """Return a cached Snowflake connection."""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="MARTS",
        role="DBT_ROLE",
    )


def _fresh_connection():
    """Drop the cached connection and create a new one."""
    get_connection.clear()
    return get_connection()


def generate_sql(question):
    """Ask the LLM to produce a SQL query for the given question."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        answer = response.choices[0].message.content
        sql = json.loads(answer)["sql"]
    except (KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"LLM returned invalid JSON: {e}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}") from e

    # Strip any schema prefix the model may have added
    sql = sql.replace("ZOMATO.MARTS.", "").replace("ZOMATO.", "")
    return sql.strip().rstrip(";")


def is_safe(sql):
    """Return True only if the SQL appears to be a read-only query."""
    lowered = sql.lower().lstrip()

    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False

    if _FORBIDDEN_RE.search(lowered):
        return False

    return True


def run_query(sql):
    """Execute a SQL query against Snowflake, with automatic reconnect."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        return cursor.execute(sql).fetch_pandas_all()
    except snowflake.connector.errors.DatabaseError:
        # Connection may have timed out — reconnect once
        conn = _fresh_connection()
        cursor = conn.cursor()
        return cursor.execute(sql).fetch_pandas_all()
    finally:
        cursor.close()


# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.title("Chat with your Zomato Data")
st.caption(f"Ask in English, {MODEL} writes the SQL, Snowflake runs it")

with st.sidebar:
    st.header("Example Questions")
    for q in EXAMPLE_QUESTIONS:
        st.markdown(f" - {q}")

question = st.text_input(
    "Enter your question here",
    placeholder="e.g. Top 10 restaurants by revenue in Bangalore",
)

if question:
    try:
        sql = generate_sql(question)
    except (ValueError, RuntimeError) as e:
        st.error(str(e))
        st.stop()

    st.code(sql, language="sql")

    if not is_safe(sql):
        st.error("The generated SQL is not safe to run. Please modify your question.")
    else:
        try:
            df = run_query(sql)
            st.success(f"{len(df)} rows returned")
            st.dataframe(df, hide_index=True)

            if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                st.bar_chart(df, x=df.columns[0], y=df.columns[1])

        except Exception as e:
            st.error(f"Error running query: {e}")