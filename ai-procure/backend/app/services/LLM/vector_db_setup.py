import os
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai

load_dotenv()

# ===== CONFIG =====
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
    raise RuntimeError("Missing environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ===== EMBEDDING GENERATOR =====

def embed_text(text: str) -> list:
    """
    Получить embedding через Gemini text-embedding-004
    Размерность: 768
    """
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"❌ Ошибка при генерации embedding: {e}")
        raise


def build_supplier_text(entry: dict) -> str:
    """
    Создать текстовое представление для registry_entry
    """
    # Имя
    if entry.get('first_name') and entry.get('last_name'):
        name = f"{entry['last_name']} {entry['first_name']} {entry.get('middle_name', '')}".strip()
    else:
        name = entry.get('general_name', 'Не указано')

    # Описание деятельности
    specialty = entry.get('specialty_description', 'Не указано')

    # Тип реестра
    registry = entry.get('source_registry', 'Не указано')

    # БИН/ИИН
    external_id = entry.get('external_id', 'Не указано')

    return f"""
Название/ФИО: {name}
Специализация: {specialty}
Реестр: {registry}
БИН/ИИН: {external_id}
""".strip()


# ===== SAVE EMBEDDING =====

def save_embedding(registry_entry_id: int, text: str, embedding: list):
    """
    Сохранить embedding в таблицу supplier_embeddings
    """
    try:
        result = supabase.table("supplier_embeddings").insert({
            "registry_entry_id": registry_entry_id,  # FIXED: было supplier_id
            "text_to_embed": text,
            "embedding": embedding
        }).execute()
        return result
    except Exception as e:
        print(f"❌ Ошибка при сохранении embedding для registry_entry_id={registry_entry_id}: {e}")
        raise


# ===== GENERATE EMBEDDINGS FOR ALL REGISTRY ENTRIES =====

def embed_all_registry_entries():
    """
    Генерировать embeddings для всех записей из таблицы registry_entries
    """
    print("Загрузка записей из таблицы 'registry_entries'...")

    try:
        response = supabase.table("registry_entries").select("*").execute()
        entries = response.data
    except Exception as e:
        print(f"Ошибка при загрузке registry_entries: {e}")
        return

    if not entries:
        print("Таблица 'registry_entries' пуста.")
        return

    print(f"Найдено записей: {len(entries)}")

    # Проверяем существующие embeddings
    existing = supabase.table("supplier_embeddings").select("registry_entry_id").execute()
    existing_ids = {item['registry_entry_id'] for item in existing.data}

    success_count = 0
    error_count = 0
    skip_count = len(existing_ids)

    for idx, entry in enumerate(entries, 1):
        entry_id = entry["id"]

        # Пропускаем, если embedding уже существует
        if entry_id in existing_ids:
            continue

        try:
            text = build_supplier_text(entry)
            embedding = embed_text(text)
            save_embedding(entry_id, text, embedding)

            success_count += 1
            if success_count % 10 == 0:
                print(f"✅ [{idx}/{len(entries)}] Обработано: {success_count}")

        except Exception as e:
            error_count += 1
            print(f"❌ [{idx}/{len(entries)}] Ошибка для entry_id={entry_id}: {e}")

    print("\n" + "="*60)
    print(f"СТАТИСТИКА:")
    print(f"   Всего записей: {len(entries)}")
    print(f"   Пропущено (уже есть): {skip_count}")
    print(f"   Успешно создано: {success_count}")
    print(f"   Ошибок: {error_count}")
    print("="*60)


# ===== GENERATE EMBEDDINGS FOR TENDERS =====

def embed_all_tenders():
    """
    Генерировать embeddings для всех тендеров
    """
    print("📥 Загрузка тендеров из таблицы 'tenders'...")

    try:
        response = supabase.table("tenders").select("*").execute()
        tenders = response.data
    except Exception as e:
        print(f"❌ Ошибка при загрузке tenders: {e}")
        return

    if not tenders:
        print("Таблица 'tenders' пуста.")
        return

    print(f"Найдено тендеров: {len(tenders)}")

    # Проверяем существующие embeddings
    existing = supabase.table("tender_embeddings").select("tender_id").execute()
    existing_ids = {item['tender_id'] for item in existing.data}

    success_count = 0
    error_count = 0

    for idx, tender in enumerate(tenders, 1):
        tender_id = tender["id"]

        if tender_id in existing_ids:
            continue

        try:
            # Создаем текст для embedding
            text = f"""
Номер: {tender.get('announce_number', '')}
Название: {tender.get('name', '')}
Заказчик: {tender.get('organizer_name', '')}
Сумма: {tender.get('total_sum', 0)}
Анализ: {tender.get('ml_analysis_text', '')[:500]}
""".strip()

            embedding = embed_text(text)

            supabase.table("tender_embeddings").insert({
                "tender_id": tender_id,
                "text_to_embed": text,
                "embedding": embedding
            }).execute()

            success_count += 1
            if success_count % 10 == 0:
                print(f"✅ [{idx}/{len(tenders)}] Обработано: {success_count}")

        except Exception as e:
            error_count += 1
            print(f"❌ [{idx}/{len(tenders)}] Ошибка для tender_id={tender_id}: {e}")

    print("\n" + "="*60)
    print(f"СТАТИСТИКА:")
    print(f"   Всего тендеров: {len(tenders)}")
    print(f"   Пропущено (уже есть): {len(existing_ids)}")
    print(f"   Успешно создано: {success_count}")
    print(f"   Ошибок: {error_count}")
    print("="*60)


# ===== CLEAR ALL EMBEDDINGS =====

def clear_all_embeddings():
    """
    Удалить все embeddings (для пересоздания)
    """
    confirm = input("Удалить ВСЕ embeddings? (yes/no): ")
    if confirm.lower() != "yes":
        print("Отменено.")
        return

    try:
        # Удаляем supplier embeddings
        result1 = supabase.table("supplier_embeddings").delete().neq("id", 0).execute()
        print(f"Удалено supplier_embeddings: {len(result1.data)}")

        # Удаляем tender embeddings
        result2 = supabase.table("tender_embeddings").delete().neq("id", 0).execute()
        print(f"Удалено tender_embeddings: {len(result2.data)}")
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")


# ===== MAIN =====

if __name__ == "__main__":
    print("🚀 Vector DB Setup - Генерация Embeddings")
    print("="*60)

    # Раскомментируйте, если нужно очистить все embeddings
    # clear_all_embeddings()

    print("\n📝 Выберите действие:")
    print("1. Создать embeddings для поставщиков (registry_entries)")
    print("2. Создать embeddings для тендеров")
    print("3. Создать embeddings для всех")

    choice = input("\nВыбор (1/2/3): ").strip()

    if choice == "1":
        embed_all_registry_entries()
    elif choice == "2":
        embed_all_tenders()
    elif choice == "3":
        embed_all_registry_entries()
        print("\n")
        embed_all_tenders()
    else:
        print("❌ Неверный выбор")

    print("\n✅ Готово!")