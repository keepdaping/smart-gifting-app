"""Rank catalogue gifts, including targeted football-apparel recommendations."""

import json
import re

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from gift_data import build_recommendation_model, load_product_catalog

FOOTBALL_QUERY_PATTERN = re.compile(
    r"\b(?:bournemouth|arsenal|jersey|kit|football|soccer)\b",
    flags=re.IGNORECASE,
)
TEAM_QUERY_PATTERN = re.compile(r"\b(?:bournemouth|arsenal)\b", re.IGNORECASE)
FOOTBALL_QUERY_EXPANSION = "football soccer team jersey shirt uniform kit fan shop"
FOOTBALL_CONTEXT_PATTERN = re.compile(
    r"\b(?:football|soccer)\b",
    re.IGNORECASE,
)
APPAREL_PATTERN = re.compile(r"\b(?:jersey|shirt|uniform|apparel|sportswear)\b", re.IGNORECASE)
JERSEY_PATTERN = re.compile(r"\bjersey\b", re.IGNORECASE)
KIT_PATTERN = re.compile(r"\bkit\b", re.IGNORECASE)
IRRELEVANT_APPAREL_PATTERN = re.compile(
    r"\b(?:pet|helmet|protective|towel)\b",
    flags=re.IGNORECASE,
)


def _get_category_label(category_value):
    """Return the first catalogue category as a compact badge label."""
    if isinstance(category_value, list):
        return str(category_value[0]) if category_value else "Gift idea"
    if not isinstance(category_value, str) or not category_value.strip():
        return "Gift idea"

    try:
        categories = json.loads(category_value)
    except json.JSONDecodeError:
        return category_value
    return str(categories[0]) if isinstance(categories, list) and categories else "Gift idea"


def recommend_gifts(
    user_query: str,
    product_df: pd.DataFrame,
    vectorizer,
    tfidf_matrix,
    top_n: int = 6,
):
    """Rank products by text similarity; football intent only returns matching apparel.

    Team names are expanded toward football apparel terms, but never fall back to
    unrelated products when the catalogue has no suitable match.
    """
    query_text = (user_query or "").strip()
    if not query_text:
        return []

    football_intent = bool(FOOTBALL_QUERY_PATTERN.search(query_text))
    if football_intent:
        query_text = f"{query_text} {FOOTBALL_QUERY_EXPANSION}"

    query_vector = vectorizer.transform([query_text])
    similarity_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()

    if football_intent:
        titles = product_df.get("title", pd.Series("", index=product_df.index)).fillna("").astype(str)
        categories = product_df.get("categories", pd.Series("", index=product_df.index)).fillna("").astype(str)
        requested_teams = TEAM_QUERY_PATTERN.findall(user_query)
        eligible_indices = [
            index
            for index, (title, category) in enumerate(zip(titles, categories))
            if (
                (
                    FOOTBALL_CONTEXT_PATTERN.search(f"{title} {category}")
                    and (APPAREL_PATTERN.search(title) or KIT_PATTERN.search(title))
                )
                or (JERSEY_PATTERN.search(title) and "fan shop" in category.lower())
            )
            and all(team.lower() in f"{title} {category}".lower() for team in requested_teams)
            and not IRRELEVANT_APPAREL_PATTERN.search(f"{title} {category}")
        ]
        if not eligible_indices:
            return []
        top_indices = sorted(
            eligible_indices,
            key=lambda index: similarity_scores[index],
            reverse=True,
        )[:top_n]
    else:
        top_indices = similarity_scores.argsort()[::-1][:top_n]

    results = product_df.iloc[top_indices].copy()
    results["similarity_score"] = similarity_scores[top_indices]
    results["product_id"] = top_indices
    if "categories" in results:
        results["category_label"] = results["categories"].map(_get_category_label)
    else:
        results["category_label"] = "Gift idea"
    return results.to_dict(orient="records")


def main():
    """Print sample recommendations to demonstrate the ranking engine."""
    product_df = load_product_catalog()
    vectorizer, tfidf_matrix = build_recommendation_model(product_df)
    test_query = "birthday gift for my brother who loves running"
    print(f"Testing recommendations for query: '{test_query}'\n")
    recommendations = recommend_gifts(
        test_query,
        product_df,
        vectorizer,
        tfidf_matrix,
        top_n=6,
    )
    for recommendation in recommendations:
        print(recommendation)


if __name__ == "__main__":
    main()