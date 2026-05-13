import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from database.vector_db import search_catalog
from google import genai
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your actual portfolio domain
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent 

FRONTEND_DIR = BASE_DIR / "Frontend" / "portfolio" 

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def read_index():
    # Serve the file from the new nested path
    return FileResponse(FRONTEND_DIR / "index.html")

# Initialize Gemini Client
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    session_id: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Step A: Search your Vector DB for relevant products
        related_products = search_catalog(request.message, top_k=2)
        
        # Step B: Format the products into a string for Gemini
        context = "Here are some relevant products we have in stock:\n"
        for p in related_products:
            context += f"- {p['title']}: Rs. {p['price']} (Link: {p['url']})\n"

        # Step C: Ask Gemini to generate a response
        system_prompt = f"""
        You are a premium e-commerce concierge. Use the following product data to help the user.
        If a product matches their needs, recommend it warmly. 
        If no products are relevant, politely guide them.
        Keep it concise and professional.
        
        Available Products:
        {context}
        """

        response = ai_client.models.generate_content(
            model="gemini-2.5-flash", 
            config={'system_instruction': system_prompt},
            contents=request.message
        )

        bot_text = response.text if hasattr(response, 'text') else "I'm sorry, I couldn't process that."

        return {"reply": bot_text}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="The concierge is momentarily unavailable.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)