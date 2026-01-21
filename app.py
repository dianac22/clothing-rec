from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
import os

app = Flask(__name__)

# Load data
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

prod_lookup = prod.set_index("sku")[["color", "size", "unit_price"]]

q1, q2 = prod["unit_price"].quantile([0.33, 0.66]).values

def price_segment(price: float) -> str:
    if price <= q1:
        return "low"
    if price <= q2:
        return "mid"
    return "premium"

prod_lookup["price_segment"] = prod_lookup["unit_price"].apply(price_segment)

# Store user interactions
user_interactions = {}

def get_recommendations(user_id, n_recommendations=5):
    """Get product recommendations for a user based on their purchase history."""
    
    if user_id not in user_interactions or len(user_interactions[user_id]) == 0:
        # Return popular products if user has no history
        return prod.nlargest(n_recommendations, "unit_price")[["sku", "color", "size", "unit_price"]].to_dict('records')
    
    # Get user's purchased items
    purchased_skus = user_interactions[user_id]
    
    # Create user profile from purchased items
    user_vectors = []
    for sku in purchased_skus:
        if str(sku) in feature_df.index:
            user_vectors.append(feature_df.loc[str(sku)].values)
    
    if not user_vectors:
        return prod.nlargest(n_recommendations, "unit_price")[["sku", "color", "size", "unit_price"]].to_dict('records')
    
    user_profile = np.mean(user_vectors, axis=0)
    
    # Calculate similarity
    similarities = cosine_similarity([user_profile], features)[0]
    
    # Get products not yet purchased
    product_scores = pd.DataFrame({
        'sku': prod['sku'].values,
        'similarity': similarities,
        'color': prod['color'].values,
        'size': prod['size'].values,
        'unit_price': prod['unit_price'].values
    })
    
    # Filter out already purchased items
    product_scores = product_scores[~product_scores['sku'].isin(purchased_skus)]
    
    # Sort by similarity and get top N
    recommendations = product_scores.nlargest(n_recommendations, 'similarity')[['sku', 'color', 'size', 'unit_price', 'similarity']].to_dict('records')
    
    return recommendations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/users', methods=['GET'])
def get_users():
    users = list(user_interactions.keys())
    return jsonify({'users': users})

@app.route('/api/add-user', methods=['POST'])
def add_user():
    data = request.json
    user_id = data.get('user_id')
    if user_id and user_id not in user_interactions:
        user_interactions[user_id] = []
        return jsonify({'status': 'success', 'message': f'User {user_id} created'})
    return jsonify({'status': 'error', 'message': 'User already exists or invalid ID'}), 400

@app.route('/api/add-purchase', methods=['POST'])
def add_purchase():
    data = request.json
    user_id = data.get('user_id')
    sku = str(data.get('sku'))
    
    if user_id not in user_interactions:
        user_interactions[user_id] = []
    
    if sku in prod['sku'].values:
        user_interactions[user_id].append(sku)
        return jsonify({'status': 'success', 'message': f'Purchase added for {user_id}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid SKU'}), 400

@app.route('/api/recommendations/<user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    n = request.args.get('n', 5, type=int)
    recs = get_recommendations(user_id, n)
    # Convert numpy types to Python native types
    for r in recs:
        r['sku'] = str(r['sku'])
        r['unit_price'] = float(r['unit_price'])
        r['color'] = str(r['color'])
        r['size'] = str(r['size'])
        if 'similarity' in r:
            r['similarity'] = float(r['similarity'])
    return jsonify({'recommendations': recs})

@app.route('/api/products', methods=['GET'])
def get_products():
    products = prod[['sku', 'color', 'size', 'unit_price']].head(50).to_dict('records')
    # Convert numpy types to Python native types
    for p in products:
        p['unit_price'] = float(p['unit_price'])
        p['sku'] = str(p['sku'])
    return jsonify({'products': products})

@app.route('/api/user-history/<user_id>', methods=['GET'])
def get_user_history(user_id):
    if user_id not in user_interactions:
        return jsonify({'history': []})
    
    history = []
    for sku in user_interactions[user_id]:
        item = prod[prod['sku'] == sku].iloc[0]
        history.append({
            'sku': str(sku),
            'color': str(item['color']),
            'size': str(item['size']),
            'unit_price': float(item['unit_price'])
        })
    
    return jsonify({'history': history})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
