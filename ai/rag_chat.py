import os

import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
NEW_REVIEWS = 500
TOP_K = 5
EMBED_BATCH_SIZE = 100  # stay well within OpenAI token limits
CACHE_FILE = "review_embeddings.parquet"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Data Layer ───────────────────────────────────────────────────────────────

def read_reviews_from_snowflake():
    """Fetch a sample of reviews from Snowflake."""
    with snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    ) as conn:
        query = f"""
            SELECT REVIEW_ID, CITY, RATING, COMMENT
            FROM ZOMATO.STAGING.STG_REVIEWS
            SAMPLE ({NEW_REVIEWS} ROWS)
        """
        df = conn.cursor().execute(query).fetch_pandas_all()

    df.columns = [col.lower() for col in df.columns]
    return df


# ── Embedding helpers ────────────────────────────────────────────────────────

def embed(texts):
    """Return embeddings for a list of strings, batching to avoid token limits."""
    all_embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        except Exception as e:
            st.error(f"Embedding API error (batch {i}): {e}")
            # Fill failed batch with zero vectors so indices stay aligned
            dim = len(all_embeddings[0]) if all_embeddings else 1536
            all_embeddings.extend([[0.0] * dim] * len(batch))
    return all_embeddings


@st.cache_data()
def load_reviews():
    """Load reviews + embeddings, using a local parquet cache when available."""
    if os.path.exists(CACHE_FILE):
        return pd.read_parquet(CACHE_FILE)

    df = read_reviews_from_snowflake()

    # Drop rows with missing comments before embedding
    df = df.dropna(subset=["comment"])
    df = df[df["comment"].str.strip() != ""]

    df["embedding"] = embed(df["comment"].tolist())
    df.to_parquet(CACHE_FILE)
    return df


# ── Similarity search ────────────────────────────────────────────────────────

def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors."""
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def find_similar_reviews(question, df):
    """Return the TOP_K most similar reviews to the question (vectorised)."""
    try:
        question_vector = np.array(embed([question])[0])
    except Exception as e:
        st.error(f"Failed to embed your question: {e}")
        return df.head(0)

    matrix = np.vstack(df["embedding"].values)
    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(question_vector)
    # Guard against zero-norm rows
    norms = np.where(norms == 0, 1e-10, norms)
    scores = matrix @ question_vector / norms

    df = df.copy()
    df["score"] = scores
    return df.nlargest(TOP_K, "score")


# ── LLM answer ───────────────────────────────────────────────────────────────

def ask_llm(question, top_reviews):
    """Send the question + retrieved reviews to the chat model."""
    context = ""
    for _, row in top_reviews.iterrows():
        context += f" ({row['city']}, {row['rating']} stars) {row['comment']}\n"

    system_prompt = (
        "Answer ONLY using the customer reviews provided. "
        "Be concise. If the reviews don't cover it, say so."
    )

    user_prompt = f"Question: {question}\n\nReviews:\n{context}"

    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ LLM request failed: {e}"


# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.title("Chat with your Zomato Reviews")
st.caption(f"Searching {NEW_REVIEWS} reviews, answering with {CHAT_MODEL}")

# Refresh button: clear the cache so fresh data is pulled from Snowflake
if st.sidebar.button("🔄 Refresh reviews"):
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    st.cache_data.clear()
    st.rerun()

review_df = load_reviews()

question = st.text_input(
    "Ask a question about your reviews:",
    placeholder="e.g. What are the most common complaints about delivery?",
)

if question:
    top_reviews = find_similar_reviews(question, review_df)

    if top_reviews.empty:
        st.warning("Could not find similar reviews. Try a different question.")
    else:
        answer = ask_llm(question, top_reviews)

        st.markdown("**Answer:**")
        st.write(answer)

        with st.expander("Reviews used to build this answer"):
            st.dataframe(
                top_reviews[["city", "rating", "comment", "score"]],
                hide_index=True,
            )