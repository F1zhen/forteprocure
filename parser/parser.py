import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime
from typing import Optional, List
from fastapi import Query
import re
import traceback
import logging
from dotenv import load_dotenv
import os
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service_role required
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app = FastAPI()


class ScrapeRequest(BaseModel):
    url: str


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def parse_price(price_str):
    """Парсинг цены из строки"""
    if not price_str:
        return 0.0
    clean = re.sub(r'[^\d.,]', '', price_str.replace(' ', ''))
    clean = clean.replace(',', '.')
    parts = clean.split('.')
    if len(parts) > 2:
        clean = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(clean)
    except:
        return 0.0


def parse_tender_general(html_content: str, source_url: str):
    """Парсинг основной информации о тендере"""
    soup = BeautifulSoup(html_content, 'html.parser')

    tender_data = {
        "announce_number": None,
        "name": None,
        "status": None,
        "organizer_name": None,
        "total_sum": 0.0,
        "publish_date": None,
        "app_end_date": None,
        "raw_url": source_url
    }

    # 1. ПОИСК НОМЕРА ОБЪЯВЛЕНИЯ
    full_text = soup.get_text()
    match = re.search(r'(\d{8}-\d{1,})', full_text)
    if match:
        tender_data["announce_number"] = match.group(1).strip()

    # 2. ПАРСИНГ ПОЛЕЙ ИЗ ФОРМ
    form_groups = soup.find_all("div", class_="form-group")
    for group in form_groups:
        label = group.find("label")
        input_field = group.find("input")
        if label and input_field:
            txt = label.get_text(strip=True).lower()
            val = input_field.get("value", "").strip()

            if "наименование" in txt:
                tender_data["name"] = val
            elif "статус" in txt:
                tender_data["status"] = val
            elif "дата публикации" in txt:
                try:
                    tender_data["publish_date"] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S").isoformat()
                except:
                    pass
            elif "окончания приема" in txt:
                try:
                    tender_data["app_end_date"] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S").isoformat()
                except:
                    pass

    return tender_data


def parse_tender_lots(html_content: str):
    """Парсинг лотов"""
    soup = BeautifulSoup(html_content, 'html.parser')
    lots_data = []
    organizer_name = None

    table = soup.find("table", class_="table")
    if not table:
        return lots_data, organizer_name

    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 9:
            continue

        try:
            # Извлекаем заказчика из первого лота
            if not organizer_name:
                organizer_name = cols[2].get_text(strip=True)

            lot_number_elem = cols[1].find('a')
            lot_number = lot_number_elem.get_text(strip=True) if lot_number_elem else cols[1].get_text(strip=True)

            lot = {
                "lot_number": lot_number,
                "name": cols[3].get_text(strip=True),
                "description": cols[4].get_text(strip=True),
                "unit_price": parse_price(cols[5].get_text(strip=True)),
                "quantity": parse_price(cols[6].get_text(strip=True)),
                "total_price": parse_price(cols[8].get_text(strip=True))
            }

            lots_data.append(lot)
        except Exception as e:
            logger.error(f"Ошибка парсинга лота: {e}")
            continue

    return lots_data, organizer_name


def parse_tender_documents(html_content: str):
    """Парсинг документов"""
    soup = BeautifulSoup(html_content, 'html.parser')
    documents_data = []
    base_url = "https://v3bl.goszakup.gov.kz"

    table = soup.find("table", class_="table")
    if not table:
        return documents_data

    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        doc_name = cols[0].get_text(strip=True)

        # Прямые ссылки
        link = cols[0].find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('//'):
                full_url = f"https:{href}"
            elif href.startswith('/'):
                full_url = f"{base_url}{href}"
            elif href.startswith('http'):
                full_url = href
            else:
                continue

            file_type = href.split('.')[-1].lower().split('?')[0]

            documents_data.append({
                "name": doc_name,
                "url": full_url,
                "file_type": file_type
            })

    # Удаляем дубликаты
    unique_documents = []
    seen_urls = set()
    for doc in documents_data:
        if doc['url'] not in seen_urls:
            seen_urls.add(doc['url'])
            unique_documents.append(doc)

    return unique_documents


# --- API ENDPOINT ---
@app.post("/api/parse-full-tender")
async def scrape_full(request: ScrapeRequest):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        logger.info(f"Начало парсинга: {request.url}")

        # 1. ОСНОВНАЯ СТРАНИЦА
        resp_general = requests.get(request.url, headers=headers, timeout=10)
        resp_general.raise_for_status()
        tender_info = parse_tender_general(resp_general.text, request.url)

        if not tender_info["announce_number"]:
            raise ValueError("Не найден номер объявления")

        logger.info(f"Найден тендер: {tender_info['announce_number']}")

        # 2. ЛОТЫ
        lots_url = f"{request.url}?tab=lots"
        resp_lots = requests.get(lots_url, headers=headers, timeout=10)
        resp_lots.raise_for_status()
        lots_info, organizer_from_lots = parse_tender_lots(resp_lots.text)

        logger.info(f"Найдено лотов: {len(lots_info)}")

        # 3. ДОКУМЕНТЫ
        docs_url = f"{request.url}?tab=documents"
        resp_docs = requests.get(docs_url, headers=headers, timeout=10)
        resp_docs.raise_for_status()
        documents_info = parse_tender_documents(resp_docs.text)

        logger.info(f"Найдено документов: {len(documents_info)}")

        # 4. ДОПОЛНЕНИЕ ДАННЫХ
        if organizer_from_lots and not tender_info["organizer_name"]:
            tender_info["organizer_name"] = organizer_from_lots

        if lots_info and tender_info["total_sum"] == 0.0:
            tender_info["total_sum"] = sum(lot["total_price"] for lot in lots_info)

        # 5. СОХРАНЕНИЕ В БД
        logger.info("Начало сохранения в БД...")

        # Проверяем, что все обязательные поля заполнены
        if not tender_info["announce_number"]:
            raise ValueError("announce_number не может быть пустым")

        # Сохраняем тендер
        try:
            logger.info(f"Сохранение тендера: {tender_info}")

            # Убираем None значения, заменяем на пустые строки
            cleaned_tender = {}
            for key, value in tender_info.items():
                if value is None:
                    if key in ["organizer_name", "name", "status"]:
                        cleaned_tender[key] = ""
                    elif key == "total_sum":
                        cleaned_tender[key] = 0.0
                else:
                    cleaned_tender[key] = value

            res_tender = supabase.table("tenders").upsert(
                cleaned_tender,
                on_conflict="announce_number"
            ).execute()

            logger.info(f"Ответ от Supabase: {res_tender}")

            if not res_tender.data:
                raise Exception("Supabase вернул пустой ответ при сохранении тендера")

            tender_id = res_tender.data[0]['id']
            logger.info(f"Тендер сохранен с ID: {tender_id}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении тендера: {e}")
            logger.error(f"Данные тендера: {tender_info}")
            raise

        # Сохраняем лоты
        if lots_info:
            try:
                for lot in lots_info:
                    lot["tender_id"] = tender_id

                # Удаляем старые лоты
                supabase.table("tender_lots").delete().eq("tender_id", tender_id).execute()

                # Вставляем новые
                res_lots = supabase.table("tender_lots").insert(lots_info).execute()
                logger.info(f"Сохранено лотов: {len(res_lots.data)}")

            except Exception as e:
                logger.error(f"Ошибка при сохранении лотов: {e}")
                logger.error(f"Данные лотов: {lots_info}")

        # Сохраняем документы
        if documents_info:
            try:
                for doc in documents_info:
                    doc["tender_id"] = tender_id

                # Удаляем старые документы
                supabase.table("tender_documents").delete().eq("tender_id", tender_id).execute()

                # Вставляем новые
                res_docs = supabase.table("tender_documents").insert(documents_info).execute()
                logger.info(f"Сохранено документов: {len(res_docs.data)}")

            except Exception as e:
                logger.error(f"Ошибка при сохранении документов: {e}")
                logger.error(f"Данные документов: {documents_info}")

        logger.info("Парсинг и сохранение завершены успешно")

        return {
            "status": "success",
            "tender": tender_info,
            "tender_id": tender_id,
            "lots_count": len(lots_info),
            "documents_count": len(documents_info)
        }

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка: {e}")
        raise HTTPException(502, detail=f"Ошибка при загрузке страницы: {e}")
    except ValueError as e:
        logger.error(f"Ошибка валидации: {e}")
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, detail=f"Внутренняя ошибка: {str(e)}")


# --- ENDPOINT ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ (для ML) ---
@app.get("/api/tenders/{tender_id}")
async def get_tender(tender_id: int):
    """Получение полных данных о тендере для ML анализа"""
    try:
        # Получаем тендер
        tender = supabase.table("tenders").select("*").eq("id", tender_id).execute()
        if not tender.data:
            raise HTTPException(404, detail="Тендер не найден")

        # Получаем лоты
        lots = supabase.table("tender_lots").select("*").eq("tender_id", tender_id).execute()

        # Получаем документы
        documents = supabase.table("tender_documents").select("*").eq("tender_id", tender_id).execute()

        return {
            "tender": tender.data[0],
            "lots": lots.data,
            "documents": documents.data
        }

    except Exception as e:
        logger.error(f"Ошибка при получении тендера: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/tenders")
async def get_all_tenders(limit: int = 100, offset: int = 0):
    """Получение списка всех тендеров"""
    try:
        tenders = supabase.table("tenders") \
            .select("*") \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return {
            "tenders": tenders.data,
            "count": len(tenders.data)
        }

    except Exception as e:
        logger.error(f"Ошибка при получении списка тендеров: {e}")
        raise HTTPException(500, detail=str(e))


from typing import Optional, List
from fastapi import Query


# ... (ваш существующий код) ...

# ==================== API ДЛЯ ML АНАЛИЗА ====================

@app.get("/api/tenders/{tender_id}/full")
async def get_tender_full_data(tender_id: int):
    """
    Получить ПОЛНЫЕ данные о тендере для ML анализа
    Включает: тендер + лоты + документы

    Пример запроса:
    GET http://127.0.0.1:8000/api/tenders/1/full
    """
    try:
        # Получаем основную информацию о тендере
        tender_result = supabase.table("tenders").select("*").eq("id", tender_id).execute()

        if not tender_result.data:
            raise HTTPException(404, detail=f"Тендер с ID {tender_id} не найден")

        tender = tender_result.data[0]

        # Получаем все лоты
        lots_result = supabase.table("tender_lots").select("*").eq("tender_id", tender_id).execute()

        # Получаем все документы
        docs_result = supabase.table("tender_documents").select("*").eq("tender_id", tender_id).execute()

        return {
            "tender": tender,
            "lots": lots_result.data,
            "documents": docs_result.data,
            "summary": {
                "total_lots": len(lots_result.data),
                "total_documents": len(docs_result.data),
                "total_sum": float(tender.get("total_sum", 0))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении данных тендера {tender_id}: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/tenders")
async def get_tenders(
        limit: int = Query(100, ge=1, le=1000, description="Количество записей"),
        offset: int = Query(0, ge=0, description="Смещение"),
        is_analyzed: Optional[bool] = Query(None, description="Фильтр по статусу анализа"),
        status: Optional[str] = Query(None, description="Фильтр по статусу тендера"),
        min_sum: Optional[float] = Query(None, description="Минимальная сумма тендера"),
        max_sum: Optional[float] = Query(None, description="Максимальная сумма тендера")
):
    """
    Получить список тендеров с фильтрацией

    Примеры запросов:
    - Все тендеры: GET /api/tenders
    - Неанализированные: GET /api/tenders?is_analyzed=false
    - С фильтром по сумме: GET /api/tenders?min_sum=1000000
    - Опубликованные: GET /api/tenders?status=Опубликовано
    """
    try:
        query = supabase.table("tenders").select("*")

        # Применяем фильтры
        if is_analyzed is not None:
            query = query.eq("is_analyzed", is_analyzed)

        if status:
            query = query.eq("status", status)

        if min_sum is not None:
            query = query.gte("total_sum", min_sum)

        if max_sum is not None:
            query = query.lte("total_sum", max_sum)

        # Сортировка и пагинация
        result = query.order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        return {
            "tenders": result.data,
            "count": len(result.data),
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Ошибка при получении списка тендеров: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/tenders/unanalyzed")
async def get_unanalyzed_tenders(limit: int = Query(50, ge=1, le=500)):
    """
    Получить все НЕАНАЛИЗИРОВАННЫЕ тендеры для ML обработки

    Пример запроса:
    GET http://127.0.0.1:8000/api/tenders/unanalyzed?limit=10
    """
    try:
        result = supabase.table("tenders") \
            .select("*") \
            .eq("is_analyzed", False) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return {
            "tenders": result.data,
            "count": len(result.data)
        }

    except Exception as e:
        logger.error(f"Ошибка при получении неанализированных тендеров: {e}")
        raise HTTPException(500, detail=str(e))


@app.get("/api/tenders/batch")
async def get_tenders_batch(tender_ids: str = Query(..., description="Список ID через запятую")):
    """
    Получить несколько тендеров сразу по списку ID

    Пример запроса:
    GET http://127.0.0.1:8000/api/tenders/batch?tender_ids=1,2,3,4,5
    """
    try:
        # Парсим ID из строки
        ids = [int(id.strip()) for id in tender_ids.split(",")]

        result = supabase.table("tenders") \
            .select("*") \
            .in_("id", ids) \
            .execute()

        return {
            "tenders": result.data,
            "count": len(result.data)
        }

    except ValueError:
        raise HTTPException(400, detail="Неверный формат ID. Используйте числа через запятую")
    except Exception as e:
        logger.error(f"Ошибка при получении батча тендеров: {e}")
        raise HTTPException(500, detail=str(e))


# ==================== API ДЛЯ СОХРАНЕНИЯ ML АНАЛИЗА ====================

class MLAnalysisUpdate(BaseModel):
    tender_id: int
    risk_score: float
    ml_analysis_text: str


@app.post("/api/tenders/update-analysis")
async def update_ml_analysis(data: MLAnalysisUpdate):
    """
    Сохранить результаты ML анализа

    Пример запроса:
    POST http://127.0.0.1:8000/api/tenders/update-analysis
    Body:
    {
        "tender_id": 1,
        "risk_score": 0.75,
        "ml_analysis_text": "Высокий риск коррупции: завышенная цена, аффилированный поставщик"
    }
    """
    try:
        result = supabase.table("tenders") \
            .update({
            "risk_score": data.risk_score,
            "ml_analysis_text": data.ml_analysis_text,
            "is_analyzed": True
        }) \
            .eq("id", data.tender_id) \
            .execute()

        if not result.data:
            raise HTTPException(404, detail=f"Тендер с ID {data.tender_id} не найден")

        return {
            "status": "success",
            "message": f"Анализ для тендера {data.tender_id} сохранен",
            "data": result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении анализа: {e}")
        raise HTTPException(500, detail=str(e))


class BatchMLAnalysis(BaseModel):
    analyses: List[MLAnalysisUpdate]


@app.post("/api/tenders/batch-update-analysis")
async def batch_update_ml_analysis(data: BatchMLAnalysis):
    """
    Массовое обновление ML анализа для нескольких тендеров

    Пример запроса:
    POST http://127.0.0.1:8000/api/tenders/batch-update-analysis
    Body:
    {
        "analyses": [
            {
                "tender_id": 1,
                "risk_score": 0.75,
                "ml_analysis_text": "Высокий риск"
            },
            {
                "tender_id": 2,
                "risk_score": 0.3,
                "ml_analysis_text": "Низкий риск"
            }
        ]
    }
    """
    try:
        updated_count = 0
        errors = []

        for analysis in data.analyses:
            try:
                result = supabase.table("tenders") \
                    .update({
                    "risk_score": analysis.risk_score,
                    "ml_analysis_text": analysis.ml_analysis_text,
                    "is_analyzed": True
                }) \
                    .eq("id", analysis.tender_id) \
                    .execute()

                if result.data:
                    updated_count += 1
                else:
                    errors.append(f"Тендер {analysis.tender_id} не найден")

            except Exception as e:
                errors.append(f"Ошибка для тендера {analysis.tender_id}: {str(e)}")

        return {
            "status": "success",
            "updated_count": updated_count,
            "total_count": len(data.analyses),
            "errors": errors if errors else None
        }

    except Exception as e:
        logger.error(f"Ошибка при массовом обновлении: {e}")
        raise HTTPException(500, detail=str(e))


# ==================== СТАТИСТИКА ====================

@app.get("/api/stats")
async def get_statistics():
    """
    Получить общую статистику по базе данных

    Пример запроса:
    GET http://127.0.0.1:8000/api/stats
    """
    try:
        # Общее количество тендеров
        all_tenders = supabase.table("tenders").select("id", count="exact").execute()

        # Количество проанализированных
        analyzed = supabase.table("tenders") \
            .select("id", count="exact") \
            .eq("is_analyzed", True) \
            .execute()

        # Количество с высоким риском (risk_score > 0.7)
        high_risk = supabase.table("tenders") \
            .select("id", count="exact") \
            .gt("risk_score", 0.7) \
            .execute()

        # Общая сумма всех тендеров
        sum_result = supabase.table("tenders").select("total_sum").execute()
        total_sum = sum(float(t.get("total_sum", 0)) for t in sum_result.data)

        # Количество лотов
        lots_count = supabase.table("tender_lots").select("id", count="exact").execute()

        # Количество документов
        docs_count = supabase.table("tender_documents").select("id", count="exact").execute()

        return {
            "total_tenders": all_tenders.count,
            "analyzed_tenders": analyzed.count,
            "unanalyzed_tenders": all_tenders.count - analyzed.count,
            "high_risk_tenders": high_risk.count,
            "total_sum": total_sum,
            "total_lots": lots_count.count,
            "total_documents": docs_count.count
        }

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        raise HTTPException(500, detail=str(e))


# ==================== ПОИСК ====================

@app.get("/api/tenders/search")
async def search_tenders(
        query: str = Query(..., min_length=3, description="Поисковый запрос"),
        limit: int = Query(20, ge=1, le=100)
):
    """
    Поиск тендеров по названию или номеру объявления

    Пример запроса:
    GET http://127.0.0.1:8000/api/tenders/search?query=строительство
    """
    try:
        # Поиск по названию
        name_results = supabase.table("tenders") \
            .select("*") \
            .ilike("name", f"%{query}%") \
            .limit(limit) \
            .execute()

        # Поиск по номеру объявления
        number_results = supabase.table("tenders") \
            .select("*") \
            .ilike("announce_number", f"%{query}%") \
            .limit(limit) \
            .execute()

        # Объединяем результаты (убираем дубликаты)
        all_results = name_results.data + number_results.data
        unique_results = {t['id']: t for t in all_results}.values()

        return {
            "results": list(unique_results),
            "count": len(unique_results)
        }

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        raise HTTPException(500, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)