import os
import io
import json
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from dotenv import load_dotenv
import google.generativeai as genai
import pdfplumber
from docx import Document

from supabase import create_client, Client

import time
import uuid

def generate_announce_number() -> str:
    # Можно как угодно, главное — не NULL
    return f"AI-{int(time.time())}-{uuid.uuid4().hex[:6]}"

#НИЦИАЛИЗАЦИЯ

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # можно anon или service_role

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY не найден в .env или переменных окружения")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL или SUPABASE_KEY не найдены в .env")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="AI-Procure API",
    description="AI-агент для анализа тендеров и закупочной документации",
    version="0.1.0",
)


#МОДЕЛИ ОТВЕТ
class AnalyzeTenderResponse(BaseModel):
    tender_id: int
    result: Dict[str, Any]


#МОДЕЛИ ДЛЯ AI-ЧАТ

class TenderChatRequest(BaseModel):
    analysis: Dict[str, Any]  # JSON из /analyze-tender
    question: str             # вопрос пользователя


class TenderChatResponse(BaseModel):
    answer: str


#ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИ

def extract_text_from_pdf_bytes(data: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx_bytes(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_upload(file: UploadFile) -> str:
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    data = file.file.read()

    if not data:
        raise ValueError("Пустой файл")

    if ext == ".pdf":
        return extract_text_from_pdf_bytes(data)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx_bytes(data)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}. Ожидается PDF или DOCX.")


def build_prompt(doc_text: str) -> str:
    # Здесь БЕЗ вопроса – сразу полный анализ
    return f"""
Ты — AI-Procure, экспертный AI-аналитик по государственным закупкам и тендерной документации.
Твоя задача — на основе текста тендера выдать СТРОГО один JSON-объект,
который бэкенд сможет парсить.

ВАЖНО:
- верни ТОЛЬКО валидный JSON, без пояснений, без комментариев, без текста до или после;
- строки в JSON — в двойных кавычках;
- не добавляй лишние поля, которых нет в схеме;
- если информации нет — ставь пустую строку "" или пустой массив [].

Требуемый формат JSON:

{{
  "summary": "краткое резюме тендера в 3–5 предложениях",
  "key_fields": {{
    "title": "название закупки",
    "customer": "заказчик",
    "budget": "бюджет (если указан)",
    "deadline": "сроки подачи заявок (если указаны)",
    "subject": "предмет закупки",
    "evaluation_criteria": "критерии оценки",
    "technical_requirements": "основные техтребования в свободном тексте",
    "qualification_requirements": "требования к квалификации",
    "contract_terms": "кратко условия договора",
    "previous_suppliers": "предыдущие поставщики, если указаны"
  }},
  "risk_analysis": [
    {{
      "risk_flag": "уникальные_технические_требования | короткие_сроки | завышенная_цена | аффилированность | ограничение_конкуренции | другое",
      "severity": 0,
      "explanation": "кратко, что за риск",
      "justification": "почему это риск, со ссылкой на формулировки из документа"
    }}
  ],
  "technical_analysis": {{
    "document_structure": "описание структуры документа (разделы, приложения и т.п.)",
    "kpi": ["список ключевых KPI, если есть"],
    "technical_spec_table": [
      {{
        "parameter": "название параметра",
        "value": "значение",
        "notes": "комментарий, если есть"
      }}
    ]
  }},
  "contract_terms_detail": {{
    "penalties": "штрафы/пени, если есть",
    "warranties": "гарантийные обязательства",
    "deadlines": "сроки выполнения работ/поставки",
    "other_terms": "важные условия договора"
  }},
  "similar_tenders": [
    {{
      "title": "название похожего тендера, если в тексте есть",
      "price": "цена/бюджет",
      "customer": "заказчик",
      "status": "прошел/не прошел/другая информация",
      "notes": "чем похож, краткое пояснение"
    }}
  ],
  "final_notes": "краткое заключение эксперта о рисках и целесообразности участия"
}}

Анализируй ТОЛЬКО текст тендера.

Текст тендера:

=== DOCUMENT_START ===
{doc_text}
=== DOCUMENT_END ===
"""


def call_gemini(doc_text: str) -> Dict[str, Any]:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",  # просим именно JSON
        },
    )

    prompt = build_prompt(doc_text)
    response = model.generate_content(prompt)

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        print("RAW LLM RESPONSE:")
        print(response.text)
        raise e

    return data


#RISK SCORE И СОХРАНЕНИЕ В БД

def compute_risk_score(analysis: Dict[str, Any]) -> float:
    """
    Простейшая эвристика:
    берем максимальный severity из risk_analysis и нормируем до 0–1.
    Если ничего нет — 0.0.
    """
    risks = analysis.get("risk_analysis") or []
    if not isinstance(risks, list) or not risks:
        return 0.0

    severities = []
    for r in risks:
        try:
            severities.append(float(r.get("severity", 0)))
        except Exception:
            continue

    if not severities:
        return 0.0

    max_sev = max(severities)
    # ожидаем, что severity 0–100
    return max(0.0, min(max_sev / 100.0, 1.0))


def parse_budget_to_float(budget_str: str) -> float:
    if not budget_str:
        return 0.0
    import re
    clean = re.sub(r"[^\d.,]", "", budget_str.replace(" ", ""))
    clean = clean.replace(",", ".")
    parts = clean.split(".")
    if len(parts) > 2:
        clean = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(clean)
    except:
        return 0.0


def save_analysis_to_db(tender_id: Optional[int], analysis: Dict[str, Any]) -> int:
    key = analysis.get("key_fields", {}) or {}

    announce_number = key.get("announce_number") or key.get("tender_number")
    if not announce_number:
        announce_number = generate_announce_number()

    base_data = {
        "announce_number": announce_number,              # 🔴 ДОБАВИЛИ
        "name": key.get("title", ""),
        "organizer_name": key.get("customer", ""),
        "total_sum": parse_budget_to_float(key.get("budget", "")),
        "risk_score": compute_risk_score(analysis),
        "ml_analysis_text": json.dumps(analysis, ensure_ascii=False),
        "is_analyzed": True,
    }

    if tender_id is None:
        res = supabase.table("tenders").insert(base_data).execute()
        if not res.data:
            raise HTTPException(500, "Не удалось создать новый тендер")
        return res.data[0]["id"]

    res_update = (
        supabase.table("tenders")
        .update(base_data)
        .eq("id", tender_id)
        .execute()
    )

    if res_update.data:
        return tender_id

    res_insert = supabase.table("tenders").insert(base_data).execute()
    if not res_insert.data:
        raise HTTPException(500, "Не удалось создать тендер (fallback)")

    return res_insert.data[0]["id"]


#ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ AI-ЧАТА

def build_chat_prompt(analysis: Dict[str, Any], question: str) -> str:
    analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)

    return f"""
Ты — AI-Procure, встроенный AI-ассистент по госзакупкам.

Тебе передан структурированный анализ тендера в формате JSON (ANALYSIS_JSON).
Пользователь задаёт вопрос о тендере. Отвечай, опираясь ТОЛЬКО на этот анализ.
Если информации в анализе нет — честно скажи, что в данных это не указано.

Типичные задачи пользователя:
- выделить самые критичные требования;
- сделать таблицу технических характеристик;
- объяснить риски и узкие места;
- подсказать, стоит ли участвовать в тендере с точки зрения условий;
- сравнить ТЗ с его продуктом, если он кратко описан в вопросе.

Требования к ответу:
- Отвечай на русском языке;
- Пиши структурировано (списки, подпункты, таблицы в Markdown, если уместно);
- Не используй формулировки вроде "как ИИ-модель";
- Не придумывай факты, которых нет в ANALYSIS_JSON.

=== ANALYSIS_JSON (анализ тендера) ===
{analysis_json}
=== КОНЕЦ ANALYSIS_JSON ===

=== ВОПРОС ПОЛЬЗОВАТЕЛЯ ===
{question}
=== КОНЕЦ ВОПРОСА ===

Сформируй полезный, прикладной ответ для пользователя.
"""


def call_gemini_chat(analysis: Dict[str, Any], question: str) -> str:
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    prompt = build_chat_prompt(analysis, question)
    response = model.generate_content(prompt)
    return response.text


#ENDPOINT АНАЛИЗА

@app.post("/analyze-tender", response_model=AnalyzeTenderResponse)
async def analyze_tender(
    file: UploadFile = File(...),
    tender_id: Optional[int] = Query(
        default=None,
        description="ID тендера в БД (если хотим привязать анализ к существующему). "
                    "Если не указан — будет создан новый тендер.",
    ),
):
    try:
        text = extract_text_from_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при извлечении текста: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Не удалось извлечь текст из файла")

    try:
        result = call_gemini(text)

        # 💾 сохраняем в БД (создаём новый или обновляем существующий)
        saved_tender_id = save_analysis_to_db(tender_id, result)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="LLM вернул невалидный JSON. Проверьте промпт или логи сервера.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AnalyzeTenderResponse(tender_id=saved_tender_id, result=result)


#ENDPOINT AI-ЧАТ

@app.post("/chat-tender", response_model=TenderChatResponse)
async def chat_tender(payload: TenderChatRequest):
    """
    AI-чат по уже проанализированному тендеру.

    Ожидает:
    {
      "analysis": { ... JSON из /analyze-tender ... },
      "question": "Ваш вопрос"
    }

    Возвращает:
    {
      "answer": "Текст ответа ассистента"
    }
    """
    try:
        answer = call_gemini_chat(payload.analysis, payload.question)
        return TenderChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка AI-ассистента: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)