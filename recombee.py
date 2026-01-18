import os
import pandas as pd
from dotenv import load_dotenv
from recombee_api_client.api_client import RecombeeClient, Region
from recombee_api_client.api_requests import (
    AddItem,
    AddItemProperty,
    AddUser,
    AddUserProperty,
    AddPurchase,
    SetItemValues,
    SetUserValues
)

load_dotenv()

DB_ID = os.getenv("RECOMBEE_DB_ID")
PRIVATE_TOKEN = os.getenv("RECOMBEE_PRIVATE_TOKEN")
REGION = Region.EU_WEST

if not DB_ID or not PRIVATE_TOKEN:
    raise ValueError("Please set RECOMBEE_DB_ID and RECOMBEE_PRIVATE_TOKEN in your .env file")

client = RecombeeClient(DB_ID, PRIVATE_TOKEN, region=REGION)
df = pd.read_csv("women_clothing_ecommerce_sales.csv")

print("=" * 60)
print("Adding item properties...")
print("=" * 60)

properties_to_add = [
    ("color", "string"),
    ("size", "string"),
    ("unit_price", "double"),
    ("order_date", "string"),
    ("quantity", "double"),
    ("revenue", "double")
]

for prop_name, prop_type in properties_to_add:
    try:
        client.send(AddItemProperty(prop_name, prop_type))
        print(f"Added '{prop_name}' property")
    except Exception as e:
        if "already exists" in str(e):
            print(f"ℹ '{prop_name}' property already exists")
        else:
            print(f"Error adding '{prop_name}' property: {e}")

# add users
print("\n" + "=" * 60)
print("Adding user properties...")
print("=" * 60)

try:
    client.send(AddUserProperty("total_spending", "double"))
    print("Added 'total_spending' property")
except Exception as e:
    if "already exists" in str(e):
        print("ℹ 'total_spending' property already exists")
    else:
        print(f"Error adding 'total_spending' property: {e}")

print("\n" + "=" * 60)
print("Adding items (clothes)...")
print("=" * 60)

products = df[["sku", "color", "size", "unit_price"]].dropna().drop_duplicates(subset=["sku"]).copy()
products["sku"] = products["sku"].astype(str)

item_success = 0
item_error = 0

for idx, row in products.iterrows():
    sku = str(row["sku"])
    try:
        client.send(AddItem(sku))
        item_success += 1
    except Exception as e:
        if "already exists" in str(e):
            item_success += 1  
        else:
            item_error += 1

print(f"Items processed: {item_success} (new or existing)")
if item_error > 0:
    print(f"Items with errors: {item_error}")

print("\n" + "=" * 60)
print("Adding users (customers)...")
print("=" * 60)

unique_users = df["order_id"].unique()
user_success = 0
user_error = 0

for user_id in unique_users:
    user_str = str(user_id)
    try:
        client.send(AddUser(user_str))
        user_success += 1
    except Exception as e:
        if "already exists" in str(e):
            user_success += 1  
        else:
            user_error += 1

print(f"Users processed: {user_success} (new or existing)")
if user_error > 0:
    print(f"Users with errors: {user_error}")

print("\n" + "=" * 60)
print("Setting item property values...")
print("=" * 60)

item_prop_success = 0
item_prop_error = 0

for idx, row in df.iterrows():
    sku = str(row["sku"])
    try:
        values = {
            "color": str(row["color"]) if pd.notna(row["color"]) else "",
            "size": str(row["size"]) if pd.notna(row["size"]) else "",
            "unit_price": float(row["unit_price"]) if pd.notna(row["unit_price"]) else 0,
            "order_date": str(row["order_date"]),
            "quantity": float(row["quantity"]),
            "revenue": float(row["revenue"])
        }
        client.send(SetItemValues(sku, values))
        item_prop_success += 1
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1} item property updates...")
    except Exception as e:
        item_prop_error += 1
        if item_prop_error <= 5:
            print(f"   Error on row {idx} (SKU {sku}): {str(e)[:80]}")

print(f"Item properties set: {item_prop_success}")
if item_prop_error > 0:
    print(f"Item property errors: {item_prop_error}")

print("\n" + "=" * 60)
print("Setting user property values...")
print("=" * 60)

user_prop_success = 0
user_prop_error = 0

for user_id in unique_users:
    user_str = str(user_id)
    user_purchases = df[df["order_id"] == user_id]
    total_spending = user_purchases["revenue"].sum()
    
    try:
        client.send(SetUserValues(user_str, {"total_spending": float(total_spending)}))
        user_prop_success += 1
    except Exception as e:
        user_prop_error += 1
        if user_prop_error <= 5:
            print(f"  Error for user {user_str}: {str(e)[:80]}")

print(f"User properties set: {user_prop_success}")
if user_prop_error > 0:
    print(f"User property errors: {user_prop_error}")

print("\n" + "=" * 60)
print("Adding purchase interactions...")
print("=" * 60)

interaction_success = 0
interaction_error = 0

for idx, row in df.iterrows():
    order_id = str(row["order_id"])
    sku = str(row["sku"])
    
    try:
        client.send(AddPurchase(order_id, sku, timestamp=row["order_date"]))
        interaction_success += 1
        
        if (idx + 1) % 100 == 0:
            print(f"  Added {idx + 1} interactions...")
    except Exception as e:
        interaction_error += 1
        if interaction_error <= 5:
            print(f"  Error adding interaction: {str(e)[:80]}")

print(f"Interactions added: {interaction_success}")
if interaction_error > 0:
    print(f"Interaction errors: {interaction_error}")

print("\n" + "=" * 60)
print("Complete Data Sync to Recombee")
print("=" * 60)
print(f"Items:            {item_success} (with {item_error} errors)")
print(f"Users:            {user_success} (with {user_error} errors)")
print(f"Item Properties:  {item_prop_success} (with {item_prop_error} errors)")
print(f"User Properties:  {user_prop_success} (with {user_prop_error} errors)")
print(f"Interactions:     {interaction_success} (with {interaction_error} errors)")
print("=" * 60)
print("All data synchronization complete!")
print("=" * 60)
