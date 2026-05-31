"""
nlp.py — NLP intelligence layer for Expense Intelligence System.

Functions
---------
categorize_expenses  : Auto-categorise transactions using keywords / embeddings.
extract_merchants    : Normalise and aggregate merchant statistics.
generate_embeddings  : Produce sentence embeddings (requires sentence-transformers).
semantic_search      : Find top-k semantically similar transactions.
"""

import json
import re

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Optional heavy imports
# ---------------------------------------------------------------------------
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
    _ST_MODEL = None  # Lazy-loaded on first use
except ImportError:
    _ST_AVAILABLE = False
    _ST_MODEL = None

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Food",
    "Travel",
    "Entertainment",
    "Healthcare",
    "Shopping",
    "Utilities",
    "Education",
    "Other",
]

CATEGORY_KEYWORDS: dict = {
    "Food": [
        "food", "restaurant", "cafe", "coffee", "lunch", "dinner", "breakfast",
        "snack", "pizza", "burger", "sushi", "meal", "eat", "dining", "swiggy",
        "zomato", "dunzo", "grocery", "supermarket", "fruits", "vegetables",
        "bakery", "canteen", "tiffin", "hotel", "diner", "biryani", "sandwich",
        "chai", "tea", "juice", "milk", "bread",
    ],
    "Travel": [
        "travel", "uber", "ola", "rapido", "cab", "auto", "taxi", "bus",
        "train", "flight", "airline", "metro", "petrol", "fuel", "diesel",
        "toll", "parking", "airbnb", "hotel stay", "booking", "makemytrip",
        "irctc", "transport", "commute", "ride", "ferry", "ticket",
    ],
    "Entertainment": [
        "movie", "cinema", "netflix", "hotstar", "amazon prime", "spotify",
        "youtube premium", "concert", "event", "game", "gaming", "steam",
        "entertainment", "theatre", "show", "streaming", "subscription",
        "disney", "hulu", "clubbing", "bar", "pub", "party", "amusement",
    ],
    "Healthcare": [
        "hospital", "clinic", "doctor", "medicine", "pharmacy", "chemist",
        "dental", "dentist", "health", "medical", "lab", "test", "diagnosis",
        "surgery", "consultation", "therapy", "physiotherapy", "gym",
        "fitness", "yoga", "wellness", "insurance", "scan", "xray",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "shopping", "clothes", "clothing",
        "electronics", "mobile", "laptop", "gadget", "accessories", "fashion",
        "apparel", "shoe", "shoes", "bag", "wallet", "watch", "jewellery",
        "furniture", "decor", "home", "appliance", "nykaa", "beauty",
        "cosmetics", "meesho",
    ],
    "Utilities": [
        "electricity", "water", "gas", "internet", "wifi", "broadband",
        "phone", "mobile recharge", "recharge", "bill", "utility",
        "maintenance", "repair", "plumber", "electrician", "rent",
        "society", "subscription fee", "postpaid", "prepaid",
    ],
    "Education": [
        "school", "college", "university", "course", "tuition", "class",
        "coaching", "books", "stationery", "library", "exam", "fee",
        "education", "training", "certification", "udemy", "coursera",
        "study", "degree", "workshop", "seminar",
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _keyword_categorise(text: str) -> str:
    """Classify a text string using keyword matching."""
    if not isinstance(text, str):
        return "Other"
    text_lower = text.lower()
    scores: dict = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1
    best_cat = max(scores, key=lambda c: scores[c])
    return best_cat if scores[best_cat] > 0 else "Other"


def _get_st_model():
    """Lazy-load the SentenceTransformer model."""
    global _ST_MODEL
    if _ST_MODEL is None and _ST_AVAILABLE:
        try:
            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            pass
    return _ST_MODEL


def _build_text_column(df: pd.DataFrame, schema: dict) -> pd.Series:
    """Combine merchant + category columns into a single text series."""
    merchant_col = schema.get("merchant_col")
    category_col = schema.get("category_col")

    parts = []
    if merchant_col and merchant_col in df.columns:
        parts.append(df[merchant_col].fillna("").astype(str))
    if category_col and category_col in df.columns:
        parts.append(df[category_col].fillna("").astype(str))

    if parts:
        return parts[0].str.cat(parts[1:], sep=" ") if len(parts) > 1 else parts[0]
    return pd.Series([""] * len(df), index=df.index)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def categorize_expenses(df: pd.DataFrame, schema: dict) -> dict:
    """Auto-categorise each transaction and return summary statistics.

    Uses sentence-transformers for semantic similarity if available,
    otherwise falls back to keyword matching.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``df_with_categories`` (not returned — categories added in-place
        to the df copy), ``category_summary``, ``available``.
        Also adds ``ai_category`` column to the returned dataframe.
    """
    try:
        df_out = df.copy()
        text_col = _build_text_column(df_out, schema)
        texts = text_col.tolist()

        model = _get_st_model()
        if model and _ST_AVAILABLE:
            try:
                # Embed transactions and category names
                txn_embeddings = model.encode(texts, show_progress_bar=False)
                cat_embeddings = model.encode(CATEGORIES, show_progress_bar=False)

                # Cosine similarity
                txn_norm = txn_embeddings / (
                    np.linalg.norm(txn_embeddings, axis=1, keepdims=True) + 1e-9
                )
                cat_norm = cat_embeddings / (
                    np.linalg.norm(cat_embeddings, axis=1, keepdims=True) + 1e-9
                )
                sim = txn_norm @ cat_norm.T  # (n_txn, n_cat)

                # For each transaction, pick best category unless score < threshold
                best_indices = np.argmax(sim, axis=1)
                best_scores = np.max(sim, axis=1)

                ai_categories = []
                for i, (idx, score) in enumerate(zip(best_indices, best_scores)):
                    if score >= 0.25:
                        ai_categories.append(CATEGORIES[idx])
                    else:
                        # Fallback to keyword for low-confidence rows
                        ai_categories.append(_keyword_categorise(texts[i]))
                method = "sentence_transformers"
            except Exception:
                ai_categories = [_keyword_categorise(t) for t in texts]
                method = "keywords"
        else:
            ai_categories = [_keyword_categorise(t) for t in texts]
            method = "keywords"

        df_out["ai_category"] = ai_categories

        # Summary statistics
        amount_col = schema.get("amount_col")
        summary: dict = {}
        total_count = len(df_out)
        for cat in CATEGORIES:
            cat_df = df_out[df_out["ai_category"] == cat]
            count = int(len(cat_df))
            pct = round(count / total_count * 100, 1) if total_count > 0 else 0.0
            total_amount = 0.0
            if amount_col and amount_col in cat_df.columns:
                total_amount = round(
                    float(
                        pd.to_numeric(cat_df[amount_col], errors="coerce").fillna(0).sum()
                    ),
                    2,
                )
            summary[cat] = {
                "count": count,
                "percentage": pct,
                "total_amount": total_amount,
            }

        return {
            "available": True,
            "method": method,
            "df_with_categories": df_out,
            "category_summary": summary,
        }

    except Exception as e:
        return {"available": False, "reason": f"Categorisation error: {e}"}


def extract_merchants(df: pd.DataFrame, schema: dict) -> dict:
    """Normalise and aggregate merchant statistics.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.

    Returns
    -------
    dict
        Keys: ``merchants`` ({merchant: {count, total_spent, avg_spent}}),
        ``available``.
    """
    merchant_col = schema.get("merchant_col")
    amount_col = schema.get("amount_col")

    if not merchant_col or merchant_col not in df.columns:
        return {"available": False, "reason": "merchant_col not found in schema/dataframe"}

    try:
        df_work = df[[merchant_col]].copy()
        if amount_col and amount_col in df.columns:
            df_work[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
        else:
            df_work["_amount"] = 0
            amount_col = "_amount"

        # Normalise merchant names
        df_work["_merchant_norm"] = (
            df_work[merchant_col]
            .astype(str)
            .str.strip()
            .str.title()
        )

        grouped = df_work.groupby("_merchant_norm")[amount_col].agg(["count", "sum", "mean"])
        grouped.columns = ["count", "total_spent", "avg_spent"]
        grouped = grouped.sort_values("total_spent", ascending=False)

        merchants: dict = {}
        for merchant, row in grouped.iterrows():
            merchants[str(merchant)] = {
                "count": int(row["count"]),
                "total_spent": round(float(row["total_spent"]), 2),
                "avg_spent": round(float(row["avg_spent"]), 2),
            }

        return {"available": True, "merchants": merchants}

    except Exception as e:
        return {"available": False, "reason": f"Merchant extraction error: {e}"}


def generate_embeddings(texts: list) -> np.ndarray | None:
    """Generate sentence embeddings for a list of strings.

    Parameters
    ----------
    texts : list of str
        Input strings to embed.

    Returns
    -------
    np.ndarray or None
        2-D float array of shape ``(len(texts), embedding_dim)``,
        or ``None`` if sentence-transformers is unavailable.
    """
    if not texts:
        return None
    model = _get_st_model()
    if model is None:
        return None
    try:
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings
    except Exception:
        return None


def semantic_search(
    query: str,
    df: pd.DataFrame,
    schema: dict,
    top_k: int = 10,
) -> list:
    """Find top-*k* transactions most semantically similar to *query*.

    Falls back to keyword search if embeddings are unavailable.

    Parameters
    ----------
    query : str
        Natural language search string.
    df : pd.DataFrame
        Cleaned expense dataframe.
    schema : dict
        Output of ``etl.infer_schema(df)``.
    top_k : int
        Number of results to return.

    Returns
    -------
    list of dict
        Matching rows as dicts, ordered by relevance.
    """
    try:
        text_col = _build_text_column(df, schema)
        texts = text_col.tolist()

        model = _get_st_model()
        if model and _ST_AVAILABLE:
            try:
                txn_embeddings = model.encode(texts, show_progress_bar=False)
                query_embedding = model.encode([query], show_progress_bar=False)

                if _FAISS_AVAILABLE:
                    dim = txn_embeddings.shape[1]
                    index = faiss.IndexFlatIP(dim)
                    faiss.normalize_L2(txn_embeddings)
                    faiss.normalize_L2(query_embedding)
                    index.add(txn_embeddings.astype(np.float32))
                    _, indices = index.search(
                        query_embedding.astype(np.float32), min(top_k, len(df))
                    )
                    indices = indices[0]
                else:
                    # Manual cosine similarity
                    txn_norm = txn_embeddings / (
                        np.linalg.norm(txn_embeddings, axis=1, keepdims=True) + 1e-9
                    )
                    q_norm = query_embedding / (
                        np.linalg.norm(query_embedding) + 1e-9
                    )
                    scores = txn_norm @ q_norm.T
                    indices = np.argsort(scores.ravel())[::-1][: top_k]

                results = []
                for idx in indices:
                    row = df.iloc[int(idx)].to_dict()
                    row["_search_index"] = int(idx)
                    results.append({k: (v if not isinstance(v, float) or not np.isnan(v) else None) for k, v in row.items()})
                return results

            except Exception:
                pass  # Fall through to keyword search

        # --- Keyword fallback ---
        query_lower = query.lower()
        matches = []
        for idx, text in enumerate(texts):
            if query_lower in str(text).lower():
                row = df.iloc[idx].to_dict()
                row["_search_index"] = idx
                matches.append(row)
                if len(matches) >= top_k:
                    break
        return matches

    except Exception as e:
        return [{"error": str(e)}]
