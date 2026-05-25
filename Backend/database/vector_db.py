import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone

load_dotenv()

ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ecommerce-catalog")
index = pc.Index(INDEX_NAME)

CONSTRAINT_MODEL = os.getenv("CONSTRAINT_MODEL", "gemini-2.5-flash")


def get_embedding(text: str) -> list[float]:
    response = ai_client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text,
        config={"output_dimensionality": 768},
    )
    return response.embeddings[0].values


def extract_search_constraints(query: str) -> dict[str, Any]:
    """
    Hybrid search: LLM extracts numeric/category constraints for Pinecone metadata filters.
    Semantic matching still uses the original query embedding.
    """
    prompt = f"""Analyze this e-commerce product search query and extract filter constraints.
Return ONLY valid JSON with these keys (use null when not specified):
- min_price: number or null (INR/Rs.)
- max_price: number or null (INR/Rs.)
- category: string or null (product type, e.g. "Polo", "Formal Shirts")

Query: "{query}"

Examples:
- "jerseys under 3000" -> {{"min_price": null, "max_price": 3000, "category": null}}
- "polo shirts between 2000 and 5000" -> {{"min_price": 2000, "max_price": 5000, "category": "Polo"}}

JSON:"""

    try:
        response = ai_client.models.generate_content(
            model=CONSTRAINT_MODEL,
            contents=prompt,
            config={"temperature": 0, "max_output_tokens": 256},
        )
        text = (response.text or "").strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        parsed = json.loads(match.group())
        return {
            "min_price": _to_float(parsed.get("min_price")),
            "max_price": _to_float(parsed.get("max_price")),
            "category": _normalize_category(parsed.get("category")),
        }
    except Exception as exc:
        print(f"Constraint extraction failed: {exc}")
        return {}


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_category(value: Any) -> str | None:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def build_metadata_filter(constraints: dict[str, Any]) -> dict[str, Any] | None:
    """Build a Pinecone metadata filter from extracted constraints."""
    clauses: list[dict[str, Any]] = []

    min_price = constraints.get("min_price")
    max_price = constraints.get("max_price")
    if min_price is not None:
        clauses.append({"price": {"$gte": min_price}})
    if max_price is not None:
        clauses.append({"price": {"$lte": max_price}})

    category = constraints.get("category")
    if category:
        clauses.append({"category": {"$eq": category}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def upsert_products(products: list[dict]) -> None:
    vectors_to_upload = []
    for product in products:
        text_to_embed = (
            f"{product['name']} - {product['description']} - Category: {product['category']}"
        )
        vector = get_embedding(text_to_embed)
        vectors_to_upload.append(
            {
                "id": product["id"],
                "values": vector,
                "metadata": {
                    "title": product["name"],
                    "price": float(product["price"]),
                    "category": product["category"],
                    "url": product["url"],
                },
            }
        )
    index.upsert(vectors=vectors_to_upload)
    print(f"Successfully upserted {len(products)} products.")


def search_catalog(
    query: str,
    top_k: int = 3,
    constraints: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Hybrid search: semantic vector query + optional metadata filters on price/category.
    """
    if constraints is None:
        constraints = extract_search_constraints(query)

    metadata_filter = build_metadata_filter(constraints)
    query_vector = get_embedding(query)

    query_kwargs: dict[str, Any] = {
        "vector": query_vector,
        "top_k": top_k,
        "include_metadata": True,
    }
    if metadata_filter:
        query_kwargs["filter"] = metadata_filter

    results = index.query(**query_kwargs)

    matches = []
    for match in results.matches:
        meta = match.metadata or {}
        matches.append(
            {
                "id": match.id,
                "score": round(match.score, 3),
                "title": meta.get("title", "Product"),
                "price": meta.get("price", "N/A"),
                "category": meta.get("category", ""),
                "url": meta.get("url", "#"),
            }
        )
    return matches


if __name__ == "__main__":
    demo_catalog = [
        {
            "id": "prod_101",
            "name": "Raw Silk Summer Tunic",
            "description": "Breathable, lightweight raw silk tunic perfect for hot weather.",
            "category": "Womens Wear",
            "price": 4500,
            "url": "/products/silk-tunic",
        },
        {
            "id": "prod_102",
            "name": "Heavy Velvet Winter Shawl",
            "description": "Deep red velvet shawl with intricate embroidery.",
            "category": "Accessories",
            "price": 8500,
            "url": "/products/velvet-shawl",
        },
        {
            "id": "prod_103",
            "name": "Minimalist Leather Wallet",
            "description": "Slim, everyday carry wallet made from full-grain leather.",
            "category": "Mens Accessories",
            "price": 2000,
            "url": "/products/leather-wallet",
        },
    ]

    print("1. Embedding and upserting dummy data to Pinecone...")
    upsert_products(demo_catalog)

    print("\n2. Hybrid search: hot weather outfit under Rs. 5000...")
    user_message = "I need something to wear to a June wedding, it's going to be very hot, under Rs. 5000."
    print(f"User asked: '{user_message}'\n")
    search_results = search_catalog(user_message)
    for res in search_results:
        print(f"Match: {res['title']} (score: {res['score']}) - Rs. {res['price']}")
