"""Load and prepare the product catalogue for TF-IDF recommendations."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

BASE_DIR = Path(__file__).resolve().parent


def resolve_default_dataset_path() -> Path:
    """Resolve the dataset path from configuration or the project default."""
    return Path(os.getenv("GIFT_DATASET_PATH", BASE_DIR / "amazon-products2.xlsx"))


def load_product_catalog(file_path: str | os.PathLike | None = None) -> pd.DataFrame:
    """Load products from Excel and normalize missing recommendation text."""
    resolved_path = Path(file_path) if file_path is not None else resolve_default_dataset_path()
    dataframe = pd.read_excel(resolved_path)
    dataframe = dataframe.loc[:, ~dataframe.columns.str.contains(r"^Unnamed")]
    dataframe["gift_text"] = dataframe["gift_text"].fillna("")
    return dataframe


def build_recommendation_model(product_df: pd.DataFrame):
    """Fit the TF-IDF vectorizer and matrix for the supplied product catalogue."""
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(product_df["gift_text"])
    return vectorizer, tfidf_matrix


