import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

# CONFIG
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=API_KEY)

# FASTAPI
app = FastAPI(
    title="Supplier Similarity Search API",
    version="1.0"
)

# ===== EMBEDDINGS =====

def embed_text(text: str) -> list[float]:
    # ВАЖНО: модель указывается как "models/..."
    res = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
    )
    return res["embedding"]


# REQUEST MODEL
class SupplierQuery(BaseModel):
    text: str
    top_k: int = 5


# API ENDPOINT: ПОХОЖИЕ ПОСТАВЩИКИ
@app.post("/api/suppliers/similar")
async def find_similar_suppliers(payload: SupplierQuery):
    try:
        query_embedding = embed_text(payload.text)

        resp = supabase.rpc(
            "similar_suppliers",   # имя функции в Postgres
            {
                "query_embedding": query_embedding,
                "limit_num": payload.top_k,
            }
        ).execute()

        return {"results": resp.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== SIMILAR TENDERS (по tender_id) =====

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
    text = f"""
Номер объявления: {tender.get("announce_number")}
Название: {tender.get("name")}
Заказчик: {tender.get("organizer_name")}
Сумма: {tender.get("total_sum")}
ML-анализ: {tender.get("ml_analysis_text") or ""}
"""
    return embed_text(text)


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
    rpc_res = supabase.rpc(
        "similar_tenders",
        {
            "query_embedding": query_embedding,
            "limit_num": payload.top_k,
        }
    ).execute()

    items = [
        SimilarTenderItem(
            tender_id=it["tender_id"],
            announce_number=it["announce_number"],
            name=it["name"],
            total_sum=float(it["total_sum"] or 0),
            distance=float(it["distance"]),
        )
        for it in rpc_res.data
        if it["tender_id"] != payload.tender_id  # исключаем сам себя
    ]

    return SimilarTendersResponse(items=items)


# ===== SIMILAR TENDERS (по тексту из поиска) =====

class SimilarTendersTextRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/similar-tenders-by-text", response_model=SimilarTendersResponse)
async def get_similar_tenders_by_text(payload: SimilarTendersTextRequest):
    # 1. embed текста, который ввёл юзер в search bar
    query_embedding = embed_text(payload.query)

    # 2. запрос к той же функции similar_tenders
    rpc_res = supabase.rpc(
        "similar_tenders",
        {
            "query_embedding": query_embedding,
            "limit_num": payload.top_k,
        }
    ).execute()

    items = [
        SimilarTenderItem(
            tender_id=it["tender_id"],
            announce_number=it["announce_number"],
            name=it["name"],
            total_sum=float(it["total_sum"] or 0),
            distance=float(it["distance"]),
        )
        for it in rpc_res.data
    ]

    return SimilarTendersResponse(items=items)
