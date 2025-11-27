import os
import json
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai

# Загружаем .env и ключ
load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

MODEL_NAME = "gemini-2.5-flash"

# Путь к этому файлу: .../backend/app/services/LLM/gemini.py
# Тогда текст лежит, например, в .../backend/app/services/extracted/techspec_81111676.txt
# parent      → .../LLM
# parent.parent → .../services
BASE_DIR = Path(__file__).resolve().parent.parent  # .../services
DOC_PATH = BASE_DIR / "extracted" / "techspec_81111676.txt"


def load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    return path.read_text(encoding="utf-8")


def ask_gemini_about_doc(doc_text: str, user_question: str) -> dict:
    """
    Отправляем текст тендера в Gemini и получаем dict (распарсенный JSON).
    """

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",  # просим именно JSON
        },
    )

    prompt = f"""
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

Вопрос пользователя:
{user_question}
"""

    response = model.generate_content(prompt)

    # Gemini вернёт JSON-строку → парсим в dict
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        # На всякий случай логируем сырую строку
        print("RAW RESPONSE FROM GEMINI:")
        print(response.text)
        raise e

    return data


if __name__ == "__main__":
    # Загружаем текст тендера
    text = load_text(DOC_PATH)

    question = "Сделай краткое резюме технических требований и перечисли ключевые параметры."

    result = ask_gemini_about_doc(text, question)

    # Красиво печатаем JSON (как его увидит бэк / логгер)
    print(json.dumps(result, ensure_ascii=False, indent=2))
