import os
import io
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

from dotenv import load_dotenv
import google.generativeai as genai
import pdfplumber
from docx import Document

#ИНИЦИАЛИЗАЦИЯ

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY не найден в .env или переменных окружения")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash"

app = FastAPI(
    title="AI-Procure API",
    description="AI-агент для анализа тендеров и закупочной документации",
    version="0.1.0",
)


#МОДЕЛИ ОТВЕТА

class AnalyzeTenderResponse(BaseModel):
    result: Dict[str, Any]


#МОДЕЛИ ДЛЯ AI-ЧАТА
class TenderChatRequest(BaseModel):
    analysis: Dict[str, Any]  # JSON из /analyze-tender
    question: str              # вопрос пользователя


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


#ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ AI-ЧАТА

def build_chat_prompt(analysis: Dict[str, Any], question: str) -> str:
    """
    Строим промпт для чат-ассистента на основе уже готового анализа тендера.
    analysis — это JSON из /analyze-tender.
    """
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
    """
    Вызов Gemini как чат-ассистента по уже проанализированному тендеру.
    """
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        # здесь можно оставить обычный text/plain вывод
    )

    prompt = build_chat_prompt(analysis, question)
    response = model.generate_content(prompt)
    return response.text


#ENDPOINT АНАЛИЗА

@app.post("/analyze-tender", response_model=AnalyzeTenderResponse)
async def analyze_tender(file: UploadFile = File(...)):
    """
    Принимает PDF/DOCX файл тендера и возвращает структурированный JSON-анализ.
    """
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
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="LLM вернул невалидный JSON. Проверьте промпт или логи сервера.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AnalyzeTenderResponse(result=result)


#ENDPOINT AI-ЧАТА

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
