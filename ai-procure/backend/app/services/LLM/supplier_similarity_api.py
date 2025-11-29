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


class SimilarTendersRequest(BaseModel):
    tender_id: int
    top_k: int = 5


class SimilarTenderItem(BaseModel):
    tender_id: int
    announce_number: str
    name: str
    total_sum: float
    distance: float


class SimilarTendersResponse(BaseModel):
    items: list[SimilarTenderItem]


def embed_tender_for_query(tender: dict) -> list[float]:
    # берём то же представление, что и в offline-скрипте
    text = f"""
Номер объявления: {tender.get("announce_number")}
Название: {tender.get("name")}
Заказчик: {tender.get("organizer_name")}
Сумма: {tender.get("total_sum")}
ML-анализ: {tender.get("ml_analysis_text") or ""}
"""
    model = genai.GenerativeModel("text-embedding-004")
    emb = model.embed_content(text)
    return emb["embedding"]


@app.post("/similar-tenders", response_model=SimilarTendersResponse)
async def get_similar_tenders(payload: SimilarTendersRequest):
    # 1. достаём тендер из БД
    res = supabase.table("tenders").select("*").eq("id", payload.tender_id).execute()
    if not res.data:
        raise HTTPException(404, "Тендер не найден")

    tender = res.data[0]

    # 2. считаем embedding для этого тендера
    query_embedding = embed_tender_for_query(tender)

    # 3. зовём Postgres-функцию similar_tenders
    rpc_res = supabase.post(
        "/rest/v1/rpc/similar_tenders",
        {
            "query_embedding": query_embedding,
            "limit_num": payload.top_k
        }
    )

    items = [
        SimilarTenderItem(
            tender_id=it["tender_id"],
            announce_number=it["announce_number"],
            name=it["name"],
            total_sum=float(it["total_sum"] or 0),
            distance=float(it["distance"]),
        )
        for it in rpc_res.data
        if it["tender_id"] != payload.tender_id  # можно исключить сам себя
    ]

    return SimilarTendersResponse(items=items)




