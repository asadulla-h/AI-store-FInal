import os
from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone

load_dotenv()

ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

index = pc.Index("ecommerce-catalog")

def get_embedding(text: str) -> list[float]:
    """Converts a text string into a 768-dimensional numerical vector."""
    response = ai_client.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )
    # Extract the numerical array from the response object
    return response.embeddings[0].values

def upsert_products(products: list[dict]):
    """Embeds and uploads a batch of products to Pinecone."""
    vectors_to_upload = []
    
    for product in products:
        # Create a rich text description for the AI to understand
        text_to_embed = f"{product['name']} - {product['description']} - Category: {product['category']}"
        vector = get_embedding(text_to_embed)
        
        # Format the data exactly as Pinecone requires
        vectors_to_upload.append({
            "id": product["id"],
            "values": vector,
            "metadata": {
                "name": product["name"],
                "price": product["price"],
                "category": product["category"],
                "url": product["url"]
            }
        })
    
    # Upload the entire batch at once for efficiency
    index.upsert(vectors=vectors_to_upload)
    print(f"Successfully upserted {len(products)} products.")

def search_catalog(query: str, top_k: int = 3):
    """Embeds the user query and finds the closest matching products."""
    query_vector = get_embedding(query)
    
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )
    
    # Clean up the output to send back to your FastAPI router
    matches = []
    for match in results.matches:
        matches.append({
            "id": match.id,
            "score": round(match.score, 3), # A score closer to 1.0 means a highly relevant match
            "name": match.metadata["name"],
            "price": match.metadata["price"],
            "url": match.metadata["url"]
        })
    return matches

# --- LOCAL TESTING BLOCK ---
# This code only runs if you execute this file directly.
if __name__ == "__main__":
    
    # A small dummy catalog to prove the concept works
    demo_catalog = [
        {
            "id": "prod_101",
            "name": "Raw Silk Summer Tunic",
            "description": "Breathable, lightweight raw silk tunic perfect for hot weather and daytime events.",
            "category": "Womens Wear",
            "price": 4500,
            "url": "/products/silk-tunic"
        },
        {
            "id": "prod_102",
            "name": "Heavy Velvet Winter Shawl",
            "description": "Deep red velvet shawl with intricate embroidery. Keeps you incredibly warm.",
            "category": "Accessories",
            "price": 8500,
            "url": "/products/velvet-shawl"
        },
        {
            "id": "prod_103",
            "name": "Minimalist Leather Wallet",
            "description": "Slim, everyday carry wallet made from full-grain leather.",
            "category": "Mens Accessories",
            "price": 2000,
            "url": "/products/leather-wallet"
        }
    ]
    
    print("1. Embedding and upserting dummy data to Pinecone...")
    upsert_products(demo_catalog)
    
    print("\n2. Testing a natural language search...")
    user_message = "I need something to wear to a June wedding, it's going to be very hot."
    print(f"User asked: '{user_message}'\n")
    
    search_results = search_catalog(user_message)
    for res in search_results:
        print(f"Match: {res['name']} (Confidence Score: {res['score']}) - Rs. {res['price']}")