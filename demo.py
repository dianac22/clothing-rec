import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_csv("women_clothing_ecommerce_sales.csv")   

df = df[["sku", "color", "size", "unit_price"]].drop_duplicates()

# preprocesare
encoder = OneHotEncoder(handle_unknown="ignore")
encoded_cat = encoder.fit_transform(df[["color", "size"]]).toarray()

scaler = MinMaxScaler()
scaled_price = scaler.fit_transform(df[["unit_price"]])

features = np.hstack([encoded_cat, scaled_price])

feature_names = list(encoder.get_feature_names_out(["color", "size"])) + ["price_scaled"]
feature_df = pd.DataFrame(features, index=df["sku"], columns=feature_names)

users = {
    "user_A": ["799", "708"],      
    "user_B": ["897", "127"],
}

for u in users:
    users[u] = [sku for sku in users[u] if sku in feature_df.index]

user_profiles = {}
for user, purchases in users.items():
    if len(purchases) == 0:
        continue
    vectors = feature_df.loc[purchases].values
    user_profiles[user] = vectors.mean(axis=0)

user_profiles_df = pd.DataFrame(user_profiles).T


similarities = cosine_similarity(user_profiles_df.values, feature_df.values)
sim_df = pd.DataFrame(similarities, index=user_profiles_df.index, columns=feature_df.index)

def recommend_for_user(user, top_k=5):
    scores = sim_df.loc[user].sort_values(ascending=False)

    scores = scores[~scores.index.isin(users[user])]
    return scores.head(top_k)

print("\n=== Recomandări pentru user_A ===")
print(recommend_for_user("user_A", top_k=5))

print("\n=== Recomandări pentru user_B ===")
print(recommend_for_user("user_B", top_k=5))
