import pdfplumber
from docx import Document
from pathlib import Path

def extract_text_from_pdf(path: str) -> str:
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)

def extract_text_from_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(path)
    else:
        raise ValueError(f"Неподдерживаемый формат: {ext}")

def save_text_to_file(text: str, source_path: str, output_dir: str = "extracted") -> str:
    source_name = Path(source_path).stem
    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / f"{source_name}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    return str(output_file)

if __name__ == "__main__":
    source_pdf = "ai-procure/backend/app/services/samples/techspec_81111676.pdf"
    text = extract_text(source_pdf)

    output_path = save_text_to_file(
        text,
        source_path=source_pdf,
        output_dir="ai-procure/backend/app/services/extracted"
    )

    print(f"Текст сохранён в: {output_path}")
