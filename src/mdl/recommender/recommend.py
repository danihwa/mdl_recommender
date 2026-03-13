from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from src.mdl.database.connection import get_db_connection

load_dotenv()

# ── Create the OpenAI client ONCE, not inside every function
# This reuses the same HTTP connection — faster and cleaner
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# ── Pydantic model: defines the exact shape we want from the parser LLM
# Think of it as a "contract" — the LLM MUST return exactly this structure
# No more json.loads() that crashes on malformed output!
class QueryFilters(BaseModel):
    search_intent: str  # core semantic meaning to embed
    min_year: int | None  # e.g. 2020, or None if not mentioned
    min_score: float | None  # e.g. 8.0, or None if not mentioned
    exclude_title: str | None  # drama user just finished / already saw


def parse_user_query(user_query: str) -> QueryFilters:
    """
    LLM #1 — Parser.

    Takes messy natural language and returns clean structured filters.
    Uses Pydantic + strict json_schema mode so it CANNOT return garbage.

    The key idea: we separate WHAT to search for (search_intent) from
    HOW to filter results (year, score, exclude). This gives vector search
    a clean semantic query instead of a query polluted with filter words.
    """
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Chinese drama expert. Extract search parameters "
                    "from the user's query. For search_intent, extract only the "
                    "semantic meaning — themes, mood, tropes. Strip out year/score "
                    "constraints, those go in their own fields."
                ),
            },
            {"role": "user", "content": user_query},
        ],
        response_format=QueryFilters,  # 👈 pass the Pydantic class directly!
    )
    return completion.choices[0].message.parsed  # already a QueryFilters object


def find_exclude_id(title: str | None) -> int:
    """
    Looks up the DB id of a drama by title so we can exclude it from results.
    Returns -1 if nothing found — our SQL function ignores -1.
    .ilike() means case-insensitive LIKE search, so "joy of life" finds "Joy of Life"
    """
    if not title:
        return -1
    supabase = get_db_connection()
    result = (
        supabase.table("dramas")
        .select("id")
        .ilike("title", f"%{title}%")
        .limit(1)
        .execute()
    )
    return result.data[0]["id"] if result.data else -1


def embed_query(text: str) -> list[float]:
    """
    Converts text into a 1536-dimensional vector using the same model
    we used when building the database. This is crucial — you MUST use
    the same model for queries as you did for the stored embeddings,
    otherwise the similarity math is meaningless.
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large",
        dimensions=1536,
    )
    return response.data[0].embedding


def vector_search(
    query_vector: list[float],
    filters: QueryFilters,
    exclude_id: int,
    match_count: int = 5,
) -> list[dict]:
    """
    Calls the match_documents SQL function we wrote in functions.sql.
    .rpc() means "Remote Procedure Call" — calling a function on the DB.
    Returns the top N most semantically similar dramas after filtering.
    """
    supabase = get_db_connection()
    result = supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_vector,
            "match_threshold": 0.3,
            "match_count": match_count,
            "filter_year": filters.min_year or 1900,
            "filter_score": filters.min_score or 0.0,
            "exclude_id": exclude_id,
        },
    ).execute()
    return result.data


def generate_recommendation(user_query: str, dramas: list[dict]) -> str:
    """
    LLM #2 — Recommender / Generator (the G in RAG).

    Gets the raw search results and writes a friendly human explanation.
    Note the cleaner prompt structure: system sets the persona/rules,
    user message contains the actual query + context data.
    This separation helps the LLM understand its role more clearly.
    """
    context = "\n\n".join(
        [
            f"Title: {d['title']} ({d['year']}) — MDL Score: {d['mdl_score']}\n"
            f"Genres: {', '.join(d['genres'])}\n"
            f"Tags: {', '.join(d['tags'][:5])}\n"  # top 5 tags, avoid clutter
            f"Synopsis: {d['synopsis']}"
            for d in dramas
        ]
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a warm, enthusiastic Chinese drama recommender. "
                    "Recommend dramas from the provided context only. "
                    "For each pick, explain specifically why it matches the user's request. "
                    "Mention the MDL score. Keep it to 3 recommendations, max 3 paragraphs total."
                ),
            },
            {
                "role": "user",
                "content": f"My request: {user_query}\n\nDramas to choose from:\n{context}",
            },
        ],
    )
    return response.choices[0].message.content


def recommend(user_query: str) -> str:
    """
    Full pipeline: Parse → Embed → Search → Generate.
    This is the only function you need to call from outside.
    """
    print("Parsing your request...")
    filters = parse_user_query(user_query)
    print(f"   Intent: '{filters.search_intent}'")
    print(
        f"   Filters: year≥{filters.min_year}, score≥{filters.min_score}, exclude='{filters.exclude_title}'"
    )
    print(f"   Raw filters: {filters.model_dump()}")

    exclude_id = find_exclude_id(filters.exclude_title)

    print("Running vector search...")
    query_vector = embed_query(filters.search_intent)
    candidates = vector_search(query_vector, filters, exclude_id)

    if not candidates:
        return (
            "Sorry, no dramas found matching those criteria. Try relaxing the filters!"
        )

    print(f"   Found {len(candidates)} candidates, generating recommendations...\n")
    return generate_recommendation(user_query, candidates)


if __name__ == "__main__":
    query = "Recommend me something like Joy of Life — political intrigue, smart male lead, no older than 2020, rating above 8"
    result = recommend(query)
    print(result)
