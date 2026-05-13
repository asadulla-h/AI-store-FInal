import json
import os
import re
import time
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from google import genai 

# Load environment variables
import pathlib
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize API Clients using the new modern SDK
client = genai.Client() # Automatically uses GEMINI_API_KEY from .env
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "ecommerce-catalog" 

# 1. FIX PINECONE 404 ERROR: Create index if it was deleted
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"Index '{INDEX_NAME}' not found. Creating it now...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=768, # Dimension for Google's text-embedding-004
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("Waiting 10 seconds for the index to initialize...")
    time.sleep(10)

index = pc.Index(INDEX_NAME)

def clean_html(raw_html):
    """Removes HTML tags from Shopify descriptions for cleaner AI context."""
    if not raw_html:
        return ""
    clean_text = re.sub('<[^<]+>', '', raw_html)
    return clean_text.strip().replace('\n', ' ')

def process_and_upload_catalog(json_filepath):
    print("Loading Weave Wardrobe catalog...")
    
    with open(json_filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    products = data.get('products', [])
    vectors_to_upsert = []
    
    print(f"Found {len(products)} products. Generating embeddings...")

    for prod in products:
        title = prod.get('title', 'Unknown Product')
        handle = prod.get('handle', '')
        
        variants = prod.get('variants', [])
        price = variants[0].get('price', '0.00') if variants else '0.00'
        
        raw_desc = prod.get('body_html', '')
        clean_desc = clean_html(raw_desc)
        
        context_string = f"Product: {title}. Description: {clean_desc}. Price: Rs. {price}."
        
        try:
            # 2. FIX GOOGLE SDK WARNING: Use the new Client structure
            embedding_response = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=context_string,
                config={'output_dimensionality': 768}
            )
            
            # Extract the raw vector array from the new response object
            vector_values = embedding_response.embeddings[0].values
            
            vectors_to_upsert.append({
                "id": str(prod['id']),
                "values": vector_values,
                "metadata": {
                    "title": title,
                    "price": price,
                    "url": f"/products/{handle}",
                    "context": context_string
                }
            })
            print(f"[SUCCESS] Processed: {title}")
            
        except Exception as e:
            print(f"[ERROR] Error processing {title}: {e}")

    if vectors_to_upsert:
        print("\nPushing data to Pinecone vector database...")
        index.upsert(vectors=vectors_to_upsert)
        print("[DONE] Database successfully seeded with new products!")

if __name__ == "__main__":
    process_and_upload_catalog("products.json")