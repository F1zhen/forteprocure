import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# EMBEDDING GENERATOR

def embed_text(text: str):
    """Получить embedding текста через Gemini"""
    model = genai.GenerativeModel("text-embedding-004")
    emb = model.embed_content(text)
    return emb["embedding"]


def build_supplier_text(s: dict) -> str:
    return f"""
Поставщик: {s.get('name')}
Деятельность: {s.get('activity_description')}
Черный список: {s.get('is_blacklisted')}
Категория: {s.get('category', '')}
"""



# SAVE EMBEDDING
def save_embedding(supplier_id: int, text: str, embedding: list):
    supabase.table("supplier_embeddings").insert({
        "supplier_id": supplier_id,
        "text_to_embed": text,
        "embedding": embedding
    }).execute()


# GENERATE EMBEDDINGS FOR ALL SUPPLIERS
def embed_all_suppliers():
    suppliers = supabase.table("supplier_embeddings").select("*").execute().data

    print(f"Найдено поставщиков: {len(suppliers)}")

    for s in suppliers:
        supplier_id = s["id"]
        text = build_supplier_text(s)
        embedding = embed_text(text)

        save_embedding(supplier_id, text, embedding)
        print(f"Embedding создан: supplier_id={supplier_id}")


# MAIN
if __name__ == "__main__":

    print("Генерация embedding для всех suppliers...")
    embed_all_suppliers()

    print("Готово!")
