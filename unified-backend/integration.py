import os
import httpx
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PARSER_API_URL = os.getenv("PARSER_API_URL", "http://localhost:8000")
SIMILARITY_API_URL = os.getenv("SIMILARITY_API_URL", "http://localhost:8002")
AI_BACKEND_URL = os.getenv("AI_BACKEND_URL", "http://localhost:8003")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
    raise RuntimeError("Missing required environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(
    title="AI-Procure Unified API",
    description="Единая точка входа для фронтенда",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TenderSearchRequest(BaseModel):
    query: str
    limit: int = 20

class TenderSearchResponse(BaseModel):
    tenders: List[Dict[str, Any]]
    count: int

class TenderAnalysisResponse(BaseModel):
    tender_id: int
    tender: Dict[str, Any]
    ai_analysis: Dict[str, Any]
    similar_tenders: List[Dict[str, Any]]
    matching_suppliers: List[Dict[str, Any]]
    risk_suppliers: List[Dict[str, Any]]

class SupplierSearchRequest(BaseModel):
    query: str
    limit: int = 10


async def call_parser_api(endpoint: str, method: str = "GET", **kwargs):
    """Вызов Parser API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{PARSER_API_URL}{endpoint}"
        if method == "GET":
            response = await client.get(url, **kwargs)
        elif method == "POST":
            response = await client.post(url, **kwargs)
        response.raise_for_status()
        return response.json()

async def call_similarity_api(endpoint: str, data: dict):
    """Вызов Similarity API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{SIMILARITY_API_URL}{endpoint}"
        response = await client.post(url, json=data)
        response.raise_for_status()
        return response.json()

def check_supplier_risk(bin_number: str) -> bool:
    """Проверка поставщика в черных списках"""
    try:
        result = supabase.table("registry_entries") \
            .select("source_registry") \
            .eq("external_id", bin_number) \
            .execute()

        for entry in result.data:
            if entry.get("source_registry") == "UNTRUSTWORTHY_SUPPLIER":
                return True
        return False
    except Exception:
        return False

@app.get("/")
async def root():
    return {
        "service": "AI-Procure Unified API",
        "status": "running",
        "endpoints": {
            "search": "/api/tenders/search",
            "analyze": "/api/tenders/{tender_id}/analyze",
            "analyze_file": "/api/analyze-tender-file",
            "suppliers": "/api/suppliers/search",
            "complete_analysis": "/api/tenders/{tender_id}/complete"
        }
    }


@app.get("/api/tenders/search", response_model=TenderSearchResponse)
async def search_tenders(
    query: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Поиск тендеров через Parser API
    """
    try:
        data = await call_parser_api(
            f"/api/tenders/search?query={query}&limit={limit}"
        )
        return TenderSearchResponse(
            tenders=data.get("results", []),
            count=data.get("count", 0)
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Parser API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tenders/{tender_id}")
async def get_tender_details(tender_id: int):
    """
    Получить детали тендера из Supabase
    """
    try:
        tender_result = supabase.table("tenders").select("*").eq("id", tender_id).execute()

        if not tender_result.data:
            raise HTTPException(404, detail="Тендер не найден")

        tender = tender_result.data[0]

        lots = supabase.table("tender_lots").select("*").eq("tender_id", tender_id).execute()
        documents = supabase.table("tender_documents").select("*").eq("tender_id", tender_id).execute()

        return {
            "tender": tender,
            "lots": lots.data,
            "documents": documents.data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/analyze-tender-file")
async def analyze_tender_file(
    file: UploadFile = File(...),
    tender_id: Optional[int] = Query(None)
):
    """
    Загрузить файл тендера и получить AI анализ
    """
    try:
        file_content = await file.read()

        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {
                'file': (file.filename, file_content, file.content_type or 'application/pdf')
            }
            params = {'tender_id': tender_id} if tender_id else {}

            response = await client.post(
                f"{AI_BACKEND_URL}/analyze-tender",
                files=files,
                params=params
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        print(f"AI Backend HTTP Error: {e}")
        print(f"Trying to connect to: {AI_BACKEND_URL}/analyze-tender")
        raise HTTPException(500, detail=f"AI Backend error: {str(e)}")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(500, detail=f"Error analyzing file: {str(e)}")

@app.get("/api/tenders/{tender_id}/complete")
async def get_complete_analysis(tender_id: int):
    """
    Полный анализ тендера:
    - Информация о тендере
    - AI анализ
    - Похожие тендеры
    - Подходящие поставщики
    - Проверка рисков поставщиков
    """
    try:
        tender_result = supabase.table("tenders").select("*").eq("id", tender_id).execute()

        if not tender_result.data:
            raise HTTPException(404, detail="Тендер не найден")

        tender = tender_result.data[0]

        import json
        ai_analysis = {}
        if tender.get("ml_analysis_text"):
            try:
                ai_analysis = json.loads(tender["ml_analysis_text"])
            except json.JSONDecodeError:
                ai_analysis = {"raw": tender["ml_analysis_text"]}

        similar_tenders = []
        try:
            similar_data = await call_similarity_api(
                "/similar-tenders",
                {"tender_id": tender_id, "top_k": 5}
            )
            similar_tenders = similar_data.get("items", [])
        except Exception as e:
            print(f"Error fetching similar tenders: {e}")

        matching_suppliers = []
        if tender.get("name"):
            try:
                supplier_data = await call_similarity_api(
                    "/api/suppliers/similar",
                    {"text": tender["name"], "top_k": 10}
                )
                matching_suppliers = supplier_data.get("results", [])
            except Exception as e:
                print(f"Error fetching suppliers: {e}")

        risk_suppliers = []
        for supplier in matching_suppliers:
            bin_number = supplier.get("external_id") or supplier.get("bin")
            if bin_number and check_supplier_risk(bin_number):
                risk_suppliers.append(supplier)

        return TenderAnalysisResponse(
            tender_id=tender_id,
            tender=tender,
            ai_analysis=ai_analysis,
            similar_tenders=similar_tenders,
            matching_suppliers=matching_suppliers,
            risk_suppliers=risk_suppliers
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/api/suppliers/search")
async def search_suppliers(request: SupplierSearchRequest):
    """
    Поиск поставщиков по тексту через vector similarity
    """
    try:
        data = await call_similarity_api(
            "/api/suppliers/similar",
            {"text": request.query, "top_k": request.limit}
        )
        return {"suppliers": data.get("results", [])}
    except httpx.HTTPError as e:
        raise HTTPException(502, detail=f"Similarity API error: {str(e)}")
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/api/suppliers/by-registry")
async def get_suppliers_by_registry(
    registry_type: str = Query(..., description="COMMODITY_PRODUCER, QUALIFIED_SUPPLIER, etc."),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Получить поставщиков по типу реестра
    """
    try:
        result = supabase.table("registry_entries") \
            .select("*") \
            .eq("source_registry", registry_type) \
            .limit(limit) \
            .execute()

        return {
            "registry_type": registry_type,
            "suppliers": result.data,
            "count": len(result.data)
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/api/suppliers/check-risk/{bin_number}")
async def check_supplier_risk_endpoint(bin_number: str):
    """
    Проверить поставщика на наличие в недобросовестных списках
    """
    try:
        is_risky = check_supplier_risk(bin_number)

        details = supabase.table("registry_entries") \
            .select("*") \
            .eq("external_id", bin_number) \
            .execute()

        return {
            "bin": bin_number,
            "is_risky": is_risky,
            "registries": details.data
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/stats")
async def get_statistics():
    """
    Общая статистика системы
    """
    try:
        tenders_count = supabase.table("tenders").select("id", count="exact").execute()
        analyzed_count = supabase.table("tenders").select("id", count="exact").eq("is_analyzed", True).execute()

        suppliers_count = supabase.table("registry_entries").select("id", count="exact").execute()
        risky_suppliers = supabase.table("registry_entries").select("id", count="exact").eq("source_registry", "UNTRUSTWORTHY_SUPPLIER").execute()

        return {
            "tenders": {
                "total": tenders_count.count,
                "analyzed": analyzed_count.count,
                "unanalyzed": tenders_count.count - analyzed_count.count
            },
            "suppliers": {
                "total": suppliers_count.count,
                "risky": risky_suppliers.count
            }
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)