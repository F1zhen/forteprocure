import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)


#EMBEDDING ФУНКЦИЯ
def embed_text(text: str):
    emb = genai.embed_content(
        model="text-embedding-004",
        content=text
    )
    return emb["embedding"]


#ТЕКСТ ДЛЯ EMBEDDING
def build_tender_text(t: dict) -> str:
    return f"""
Номер объявления: {t.get("announce_number")}
Название: {t.get("name")}
Заказчик: {t.get("organizer_name")}
Сумма: {t.get("total_sum")}
ML-анализ: {t.get("ml_analysis_text") or ""}
"""


#ГЕНЕРАЦИЯ EMBEDDINGS
def generate_embeddings_for_all_tenders():
    res = supabase.table("tenders").select("*").execute()
    tenders = res.data
    print("Найдено тендеров:", len(tenders))

    for t in tenders:
        tid = t["id"]

        # уже есть embedding — пропускаем
        existing = (
            supabase.table("tender_embeddings")
            .select("id")
            .eq("tender_id", tid)
            .execute()
        )
        if existing.data:
            print(f" → tender_id={tid} уже имеет embedding, пропускаю")
            continue

        text = build_tender_text(t)
        try:
            embedding = embed_text(text)

            supabase.table("tender_embeddings").insert({
                "tender_id": tid,
                "text_to_embed": text,
                "embedding": embedding
            }).execute()

            print("✓ embedding создан для tender_id =", tid)

        except Exception as e:
            print("Ошибка при обработке tender_id=", tid)
            print(e)


if __name__ == "__main__":
    generate_embeddings_for_all_tenders()
