from fastembed import TextEmbedding
import psycopg2
from spellchecker import SpellChecker
from collections import defaultdict
import re
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db.bojkrogoypatbigatfrp.supabase.co"),
    "database": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": int(os.getenv("DB_PORT", 5432)),
}

embedder = TextEmbedding("BAAI/bge-small-en-v1.5")
spell = SpellChecker()

NO_MATCH_SCORE = 0.60
SQL_K = 120
PER_BOOK_LIMIT = 5
MAX_RESULTS = 20

# ----------------------------
# Stopwords for keyword extraction
# ----------------------------
STOPWORDS = {
    "the","is","in","at","on","a","an","of","to","and","or",
    "for","with","his","her","their","this","that","it","as",
    "are","was","were","be","by","from","but","not"
}

# ----------------------------
# Spell Correction
# ----------------------------
def correct_query(q):
    return " ".join(spell.correction(w) or w for w in q.split())

# ----------------------------
# Extract Keywords Automatically    
# ----------------------------
def extract_keywords(query):
    words = re.findall(r'\b\w+\b', query.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

# ----------------------------
# Clean PDF Text
# ----------------------------
def clean_content(text):
    text = text.replace("\x00", "")
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'([a-zA-Z])\s+([a-zA-Z])', r'\1\2', text)
    return text.strip()

# ----------------------------
# Extract Snippet Around Keyword
# ----------------------------
def extract_snippet(content, keywords, window=350):

    content_lower = content.lower()

    for word in keywords:
        idx = content_lower.find(word)
        if idx != -1:
            start = max(0, idx - window // 2)
            end = min(len(content), idx + window // 2)
            return content[start:end]

    return content[:window]

# ----------------------------
# Hybrid Search
# ----------------------------
def search_books(query):

    if not query:
        return {"type": "invalid"}

    keywords = extract_keywords(query)

    expanded = f"{query} in python programming with examples"
    q_emb = list(embedder.embed([expanded]))[0].tolist()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 
            book_name,
            category,
            page_number,
            chapter_name,
            content,
            1 - (embedding <=> %s::vector) AS vector_score,
            ts_rank(tsv, plainto_tsquery('english', %s)) AS keyword_score
        FROM books
        ORDER BY 
            (0.6 * (embedding <=> %s::vector) * -1 +
             0.4 * ts_rank(tsv, plainto_tsquery('english', %s))) DESC
        LIMIT %s;
        """,
        (q_emb, query, q_emb, query, SQL_K)
    )

    rows = cur.fetchall()
    conn.close()

    results = []

    for book, category, page, chapter_name, content, vector_score, keyword_score in rows:

        hybrid_score = (0.6 * vector_score) + (0.4 * keyword_score)

        # Keyword Boosting
        content_lower = content.lower()
        match_count = sum(1 for kw in keywords if kw in content_lower)

        hybrid_score += 0.03 * match_count

        if hybrid_score >= NO_MATCH_SCORE:
            results.append(
                (book, category, page, chapter_name, content, hybrid_score, keywords)
            )

    if not results:
        return {"type": "not_found"}

    results.sort(key=lambda x: x[5], reverse=True)

    final_results = []
    book_counter = defaultdict(int)

    for row in results:
        book_name = row[0]

        if book_counter[book_name] < PER_BOOK_LIMIT:
            final_results.append(row)
            book_counter[book_name] += 1

        if len(final_results) >= MAX_RESULTS:
            break

    return {"type": "answer", "data": final_results}

# ----------------------------
# CLI LOOP
# ----------------------------
if __name__ == "__main__":

    print("Multi-Book Hybrid Retrieval System")
    print("Type 'exit' to quit\n")

    while True:

        raw_query = input("Enter query: ").strip().lower()

        if raw_query == "exit":
            break

        corrected_query = correct_query(raw_query)

        if corrected_query != raw_query:
            print(f"Suggested correction: {corrected_query}\n")

        result = search_books(corrected_query)

        if result["type"] == "invalid":
            print("Please enter a meaningful question.\n")
            continue

        if result["type"] == "not_found":
            print("No relevant content found.\n")
            continue

        print("\nSearch Results")
        print("=" * 90)

        for book, category, page, chapter_name, content, score, keywords in result["data"]:

            cleaned = clean_content(content)
            snippet = extract_snippet(cleaned, keywords)

            print(f"Book       : {book}")
            print(f"Category   : {category}")
            print(f"Chapter    : {chapter_name if chapter_name else 'Not specified'}")
            print(f"Page       : {page}")
            print(f"Relevance  : {score:.2f}")
            print("-" * 90)

            print(snippet)
            print("\n" + "=" * 90 + "\n")
