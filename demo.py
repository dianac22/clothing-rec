import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("women_clothing_ecommerce_sales.csv")

prod = df[["sku", "color", "size", "unit_price"]].dropna().drop_duplicates(subset=["sku"]).copy()
prod["sku"] = prod["sku"].astype(str)

encoder = OneHotEncoder(handle_unknown="ignore")
encoded_cat = encoder.fit_transform(prod[["color", "size"]]).toarray()

scaler = MinMaxScaler()
scaled_price = scaler.fit_transform(prod[["unit_price"]])

features = np.hstack([encoded_cat, scaled_price])
feature_names = list(encoder.get_feature_names_out(["color", "size"])) + ["price_scaled"]

feature_df = pd.DataFrame(features, index=prod["sku"], columns=feature_names)

# lookup table for explainability
prod_lookup = prod.set_index("sku")[["color", "size", "unit_price"]]

q1, q2 = prod["unit_price"].quantile([0.33, 0.66]).values

def price_segment(price: float) -> str:
    if price <= q1:
        return "low"
    if price <= q2:
        return "mid"
    return "premium"

prod_lookup["price_segment"] = prod_lookup["unit_price"].apply(price_segment)

interactions = pd.DataFrame(
    [
        # Flow 1: user_A purchases
        {"user_id": "user_A", "sku": "799", "event_type": "purchase", "event_time": "2026-01-10 10:00:00"},
        {"user_id": "user_A", "sku": "708", "event_type": "purchase", "event_time": "2026-01-12 18:30:00"},

        # Flow 2: user_B purchases + views something else (session shift)
        {"user_id": "user_B", "sku": "897", "event_type": "purchase", "event_time": "2026-01-08 12:10:00"},
        {"user_id": "user_B", "sku": "127", "event_type": "purchase", "event_time": "2026-01-09 09:20:00"},
        {"user_id": "user_B", "sku": "500", "event_type": "view",     "event_time": "2026-01-18 11:05:00"},  # choose an existing sku
    ]
)

interactions["sku"] = interactions["sku"].astype(str)
interactions["event_time"] = pd.to_datetime(interactions["event_time"])

# keep only interactions with skus present in feature table
interactions = interactions[interactions["sku"].isin(feature_df.index)].copy()

EVENT_WEIGHTS = {
    "view": 0.2,
    "add_to_cart": 0.6,
    "purchase": 1.0,
}

def build_user_profile(user_id: str, interactions_df: pd.DataFrame) -> np.ndarray | None:
    ui = interactions_df[interactions_df["user_id"] == user_id].copy()
    if ui.empty:
        return None

    ui["w"] = ui["event_type"].map(EVENT_WEIGHTS).fillna(0.0)

    ui = ui[ui["w"] > 0]
    if ui.empty:
        return None

    V = feature_df.loc[ui["sku"]].values
    w = ui["w"].values.reshape(-1, 1)

    profile = (V * w).sum(axis=0) / w.sum()
    return profile

def get_user_consumed_skus(user_id: str, interactions_df: pd.DataFrame) -> set[str]:
    ui = interactions_df[(interactions_df["user_id"] == user_id) & (interactions_df["event_type"] == "purchase")]
    return set(ui["sku"].astype(str).tolist())

def dominant_price_segment(user_id: str, interactions_df: pd.DataFrame) -> str | None:
    ui = interactions_df[(interactions_df["user_id"] == user_id)]
    if ui.empty:
        return None

    purchases = ui[ui["event_type"] == "purchase"]
    base = purchases if not purchases.empty else ui

    segs = []
    for sku in base["sku"].astype(str):
        if sku in prod_lookup.index:
            segs.append(prod_lookup.loc[sku, "price_segment"])
    if not segs:
        return None
    return pd.Series(segs).mode().iloc[0]

def top_contributing_features(user_profile: np.ndarray, item_vector: np.ndarray, top_n: int = 3) -> list[tuple[str, float]]:
    # explanation: elementwise product shows where both are high
    contrib = user_profile * item_vector
    idx = np.argsort(contrib)[::-1][:top_n]
    return [(feature_names[i], float(contrib[i])) for i in idx]

def format_recommendation_row(sku: str, score: float, user_profile: np.ndarray) -> dict:
    row = {"sku": sku, "score": float(score)}
    if sku in prod_lookup.index:
        row.update({
            "color": prod_lookup.loc[sku, "color"],
            "size": prod_lookup.loc[sku, "size"],
            "unit_price": float(prod_lookup.loc[sku, "unit_price"]),
            "price_segment": prod_lookup.loc[sku, "price_segment"],
        })

    item_vec = feature_df.loc[sku].values
    top_feats = top_contributing_features(user_profile, item_vec, top_n=3)
    row["why_top_features"] = ", ".join([f"{name}" for name, _ in top_feats])
    return row

def recommend_for_user(
    user_id: str,
    interactions_df: pd.DataFrame,
    top_k: int = 5,
    exclude_consumed: bool = True,
    price_filter: bool = False,
    allow_adjacent_segment: bool = True,  # low->mid, mid->(low/premium), premium->mid
) -> pd.DataFrame:
    profile = build_user_profile(user_id, interactions_df)
    if profile is None:
        return pd.DataFrame(columns=["sku", "score", "color", "size", "unit_price", "price_segment", "why_top_features"])

    # cosine similarity to all items
    sims = cosine_similarity(profile.reshape(1, -1), feature_df.values).flatten()
    scores = pd.Series(sims, index=feature_df.index).sort_values(ascending=False)

    if exclude_consumed:
        consumed = get_user_consumed_skus(user_id, interactions_df)
        scores = scores[~scores.index.isin(consumed)]

    if price_filter:
        seg = dominant_price_segment(user_id, interactions_df)
        if seg is not None:
            if allow_adjacent_segment:
                allowed = {
                    "low": {"low", "mid"},
                    "mid": {"low", "mid", "premium"},
                    "premium": {"mid", "premium"},
                }[seg]
            else:
                allowed = {seg}

            allowed_skus = prod_lookup[prod_lookup["price_segment"].isin(allowed)].index.astype(str)
            scores = scores[scores.index.isin(allowed_skus)]

    recs = []
    for sku, score in scores.head(top_k).items():
        recs.append(format_recommendation_row(sku, score, profile))

    return pd.DataFrame(recs)

# outputs for 3 separate flows
print("\n=== Flow 1: user_A (purchase-driven) - no price filter ===")
print(recommend_for_user("user_A", interactions, top_k=5, price_filter=False).to_string(index=False))

print("\n=== Flow 3: user_A with price-segment filter (low/mid/premium constraint) ===")
print(recommend_for_user("user_A", interactions, top_k=5, price_filter=True).to_string(index=False))

print("\n=== Flow 2: user_B after a VIEW (weighted profile shift) ===")
print(recommend_for_user("user_B", interactions, top_k=5, price_filter=False).to_string(index=False))

print("\n=== Modelul utilizatorului (extragere din 'DB'): user_A interactions ===")
print(interactions[interactions["user_id"] == "user_A"].sort_values("event_time", ascending=False).to_string(index=False))
