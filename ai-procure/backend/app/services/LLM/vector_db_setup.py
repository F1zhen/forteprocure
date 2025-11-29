import os
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



# INIT VECTOR TABLE and FUNCTION

def init_vector_schema():
    sql = """
    create extension if not exists vector;

    create table if not exists supplier_embeddings (
      id bigserial primary key,
      supplier_id bigint references suppliers(id) on delete cascade,
      text_to_embed text,
      embedding vector(1536),
      created_at timestamp default now()
    );

    create or replace function similar_suppliers(
      query_embedding vector(1536),
      limit_num int
    )
    returns table(
      supplier_id bigint,
      name text,
      activity_description text,
      is_blacklisted boolean,
      distance float
    )
    language sql stable
    as $$
      select s.id as supplier_id,
             s.name,
             s.activity_description,
             s.is_blacklisted,
             (e.embedding <=> query_embedding) as distance
      from supplier_embeddings e
      join suppliers s on s.id = e.supplier_id
      order by e.embedding <=> query_embedding
      limit limit_num
    $$;
    """

    return supabase.post("/rest/v1/rpc/exec_sql", {"sql": sql})



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
    suppliers = supabase.table("suppliers").select("*").execute().data

    print(f"Найдено поставщиков: {len(suppliers)}")

    for s in suppliers:
        supplier_id = s["id"]
        text = build_supplier_text(s)
        embedding = embed_text(text)

        save_embedding(supplier_id, text, embedding)
        print(f"✓ Embedding создан: supplier_id={supplier_id}")


# MAIN
if __name__ == "__main__":
    print("→ Создание схемы vector DB...")
    out = init_vector_schema()
    print(out)

    print("→ Генерация embedding для всех suppliers...")
    embed_all_suppliers()

    print("✓ Готово!")
