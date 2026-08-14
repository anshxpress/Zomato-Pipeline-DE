import os
import json
import snowflake.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL =  "gpt-4o-mini"
SAMPLE_N = 5
client = OpenAI()

TOPICS = "food quality, delivery speed, packaging, customer service, or other"
SYSTEM_PROMPT = f"""
you classify customer review for a food delivery app.

For the revire you are given, return:
- sentiment_label: positive, negative or neutral
- sentiment_score: a number between -1.0 and 1.0
- topic: one of {TOPICS}
- key_issue: a short phase of 6 words or less that describe the main issue in the review, if any, otherwise null
- review_summary: a short phase of 10 words or less that describe the review, otherwise null

reply in JSON in this exact format:
{{
    "sentiment_label": "<sentiment_label>",
    "sentiment_score": <sentiment_score>,
    "topic": "<topic>",
    "key_issue": "<key_issue>"
}}
"""

def get_connection():
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        password=os.getenv("SNOWFLAKE_PASSWORD")
    )
    return conn

def create_output_table(cursor):
    cursor.execute("CREATE SCHEMA IF NOT EXISTS ZOMATO.AI")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ZOMATO.AI.REVIEW_ENRICHED(
        REVIEW_ID NUMBER,
        SENTIMENT_LABEL VARCHAR,
        SENTIMENT_SCORE NUMBER,
        TOPIC VARCHAR,
        KEY_ISSUE VARCHAR,
        MODEL VARCHAR,
        ENRICHED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
    )
    """)
    
def get_reviews_to_enrich(cursor):
    cursor.execute(f"""
        SELECT REVIEW_ID, COMMENT
        FROM ZOMATO.RAW.REVIEWS
        WHERE REVIEW_ID NOT IN (SELECT REVIEW_ID FROM ZOMATO.AI.REVIEW_ENRICHED)
        LIMIT {SAMPLE_N}
    """)

    return cursor.fetchall()

def classify_review(comment):
    response = client.chat.completions.create(
        model= MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content":SYSTEM_PROMPT},
            {"role": "user", "content": comment}
        ]
    )

    answer = response.choices[0].message.content
    return json.loads(answer)

def save_results(cursor, results):
    """Insert all the enriched rows into Snowflake in one go."""
    print(f"Saving {len(results)} enriched reviews to Snowflake...")
    cursor.executemany(
        """
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED
            (review_id, sentiment_label, sentiment_score, topic, key_issue, model)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        results,
    )
 

def main():
    conn = get_connection()
    cursor = conn.cursor()
    create_output_table(cursor)
    reviews = get_reviews_to_enrich(cursor)

    if len(reviews) == 0:
        print("No new reviews to enrich.")
        return

    print(f"Enriching {len(reviews)} reviews...")

    results = []
    for review_id, comment in reviews:
        print(f"Classifying review {review_id}: {comment}")
        try:
            labels = classify_review(comment)
            print(f"Labels for review {review_id}: {labels}")
            results.append((
                review_id,
                labels["sentiment_label"],
                labels["sentiment_score"],
                labels["topic"],
                labels["key_issue"],
                MODEL
            ))
        except Exception as e:
            print(f"Error occurred while classifying review {review_id}: {e}")

    save_results(cursor, results)
    print(f"Saved {len(results)} enriched reviews to Snowflake.")
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()


