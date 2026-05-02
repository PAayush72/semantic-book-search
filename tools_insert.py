from fastembed import TextEmbedding
import psycopg2
from pypdf import PdfReader
from pathlib import Path
import re
import os
from dotenv import load_dotenv

load_dotenv()

# =========================
# DB CONFIG
# =========================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db.bojkrogoypatbigatfrp.supabase.co"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432)),
}

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")

# =========================
# PDF READER
# =========================
def read_pdf(path):
    reader = PdfReader(path)
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()

        if text:
            # Remove NULL characters
            text = text.replace("\x00", "")

            # Normalize encoding issues
            text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")

            # Remove excessive whitespace
            text = " ".join(text.split())

            pages.append((i + 1, text))

    return pages


# =========================
# CHUNKING
# =========================
def chunk_text(text, chunk_size=250, overlap=50):
    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap

    return chunks


# =========================
# INSERT SINGLE BOOK
# =========================
def detect_chapter(text):

    lines = text.split("\n")

    for line in lines[:10]:
        line = line.strip()

        # Match CHAPTER X Title
        match = re.match(r'^(CHAPTER\s+\d+\s+[A-Za-z ]+)', line, re.IGNORECASE)

        if match:
            chapter = match.group(1)

            # Limit length to avoid paragraph capture
            chapter = chapter.split(".")[0]
            chapter = chapter[:100].strip()

            return chapter

    return None

def insert_book(pdf_path, book_name, category):
    print(f"Inserting: {book_name}")

    pages = read_pdf(pdf_path)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    current_chapter = "Unknown"

    for page_num, text in pages:

        # Detect chapter
        detected = detect_chapter(text)
        if detected:
            current_chapter = detected

        chunks = chunk_text(text)

        if not chunks:
            continue

        embeddings = list(embedder.embed(chunks))

        for chunk, emb in zip(chunks, embeddings):

            chunk = chunk.replace("\x00", "")

            if not chunk.strip():
                continue

            cur.execute(
                """
                INSERT INTO books 
                (book_name, category, chapter_name, page_number, content, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (book_name, category, current_chapter, page_num, chunk, emb.tolist())
            )

    conn.commit()
    cur.close()
    conn.close()

    print(f"{book_name} inserted successfully.\n")


# =========================
# INSERT MULTIPLE BOOKS
# =========================
def insert_multiple_books(book_list):
    for book in book_list:
        insert_book(
            pdf_path=book["path"],
            book_name=book["name"],
            category=book["category"]
        )


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    books_to_insert = [
        {
            "path": "Abraham-Silberschatz-Henry-F.-Korth-S.-Sudarshan-Database-System-Concepts-McGraw-Hill-Education-2019.pdf",
            "name": "Abraham-Silberschatz-Henry-F.-Korth-S.-Sudarshan-Database-System-Concepts-McGraw-Hill-Education-2019",
            "category": "Novel"
        },
        {
            "path": "Abraham-Silberschatz-Operating-System-Concepts-10th-2018.pdf",
            "name": "Abraham-Silberschatz-Operating-System-Concepts-10th-2018",
            "category": "OS"
        },
        {
            "path": "Advanced_Search_Methods_RAG.pdf",
            "name": "Advanced_Search_Methods_RAG",
            "category": "Search Methods"
        },
        {
            "path": "Alice_in_Wonderland.pdf",
            "name": "Alice_in_Wonderland",
            "category": "Novel"
        },
        {
            "path": "Computer_Networking_A_Top-Down_Approach_Ross.pdf",
            "name": "Computer_Networking_A_Top-Down_Approach_Ross",
            "category": "Networking"
        },
        {
            "path": "Fundamentals of Physics — Halliday & Resnick.pdf",
            "name": "Fundamentals of Physics — Halliday & Resnick",
            "category": "Physics"
        },
        {
            "path": "Manifesto.pdf",
            "name": "Manifesto",
            "category": "Novel"
        },
        {
            "path": "Mill, On Liberty.pdf",
            "name": "Mill, On Liberty",
            "category": "Novel"
        }
    ]

    insert_multiple_books(books_to_insert)
