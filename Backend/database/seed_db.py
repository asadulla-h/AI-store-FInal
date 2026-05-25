import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone, ServerlessSpec

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

client = genai.Client()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ecommerce-catalog")


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean_text = re.sub("<[^<]+>", "", raw_html)
    return clean_text.strip().replace("\n", " ")


def resolve_category(prod: dict) -> str:
    product_type = (prod.get("product_type") or "").strip()
    if product_type:
        return product_type
    tags = prod.get("tags") or []
    if tags:
        return str(tags[0]).strip()
    return "Uncategorized"


def resolve_price(variants: list) -> float:
    if not variants:
        return 0.0
    try:
        return float(variants[0].get("price", "0"))
    except (TypeError, ValueError):
        return 0.0


existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"Index '{INDEX_NAME}' not found. Creating it now...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    print("Waiting 10 seconds for the index to initialize...")
    time.sleep(10)

index = pc.Index(INDEX_NAME)


def process_and_upload_catalog(json_filepath: str) -> None:
    print("Loading catalog...")
    path = Path(json_filepath)
    if not path.is_absolute():
        path = Path(__file__).parent / json_filepath

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    products = data.get("products", [])
    vectors_to_upsert = []

    print(f"Found {len(products)} products. Generating embeddings...")

    for prod in products:
        title = prod.get("title", "Unknown Product")
        handle = prod.get("handle", "")
        variants = prod.get("variants", [])
        price = resolve_price(variants)
        category = resolve_category(prod)

        raw_desc = prod.get("body_html", "")
        clean_desc = clean_html(raw_desc)
        if len(clean_desc) > 1200:
            clean_desc = clean_desc[:1200] + "..."

        # Embed semantic text only — price/category live in metadata for hybrid filters
        text_to_embed = (
            f"Product: {title}. Description: {clean_desc}. Category: {category}."
        )

        try:
            embedding_response = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text_to_embed,
                config={"output_dimensionality": 768},
            )
            vector_values = embedding_response.embeddings[0].values

            vectors_to_upsert.append(
                {
                    "id": str(prod["id"]),
                    "values": vector_values,
                    "metadata": {
                        "title": title,
                        "price": price,
                        "category": category,
                        "url": f"/products/{handle}",
                    },
                }
            )
            print(f"[SUCCESS] Processed: {title} (Rs. {price}, {category})")

        except Exception as e:
            print(f"[ERROR] Error processing {title}: {e}")

    if vectors_to_upsert:
        print("\nPushing data to Pinecone vector database...")
        index.upsert(vectors=vectors_to_upsert)
        print("[DONE] Database successfully seeded with structured metadata!")


if __name__ == "__main__":
    process_and_upload_catalog("products.json")
