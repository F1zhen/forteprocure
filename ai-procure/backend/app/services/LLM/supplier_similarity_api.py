import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from supabase import create_client, Client
import google.generativeai as genai


# CONFIG

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Supabase env переменные не найдены")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY не найден")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
genai.configure(api_key=GEMINI_API_KEY)


# FASTAPI
app = FastAPI(
    title="Supplier Similarity Search API",
    version="1.0"
)


# EMBED TEXT
def embed_text(text: str):
    model = genai.GenerativeModel("text-embedding-004")
    emb = model.embed_content(text)
    return emb["embedding"]


# REQUEST MODEL
class SupplierQuery(BaseModel):
    text: str
    top_k: int = 5


# API ENDPOINT
@app.post("/api/suppliers/similar")
async def find_similar_suppliers(payload: SupplierQuery):
    try:
        query_embedding = embed_text(payload.text)

        resp = supabase.post(
            "/rest/v1/rpc/similar_suppliers",
            {
                "query_embedding": query_embedding,
                "limit_num": payload.top_k
            }
        )

        return {"results": resp.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# RUN

if __name__ == "__main__":

