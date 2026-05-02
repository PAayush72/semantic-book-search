# Semantic Book Search

MultiBook Hybrid Retrieval System – Complete Guide

## 1. Overview
This document explains how the MultiBook Retrieval System works. The program allows users to search across multiple books using both semantic (vector) search and keyword search. The system then combines both signals to return accurate results with page number, chapter name, and content snippets.

## 2. System Architecture
* User enters a query
* Query is spell corrected (Used because it shows irrelevant data if spelling mistake)
* Keywords are extracted
* Query is converted into a vector (semantic meaning)
* Database performs vector similarity search
* Database performs keyword (full-text) search using tsvector
* Hybrid score combines both results
* Best matching chunks are returned

## 3. What are Vectors?
A vector is a list of numbers that represents the meaning of text. The embedding model converts text into a high-dimensional vector. If two texts have similar meaning, their vectors will be close together in space. The system uses cosine distance (via pgvector operator `<=>`) to measure similarity.

## 4. What is tsvector?
`tsvector` is PostgreSQL's full-text search format. It stores tokenized words from the content along with their positions. When a query is executed, PostgreSQL converts the query into `tsquery` and matches it against the `tsvector` column using linguistic rules like stemming and stopword removal. The `ts_rank` function calculates keyword relevance.

## 5. Hybrid Search
Hybrid search combines semantic similarity and keyword relevance. In this program, the final score is calculated as: `0.6 × vector similarity + 0.4 × keyword relevance`. This ensures results are both contextually relevant and textually accurate.

## 6. Data Flow in the Program
1. User query is cleaned and corrected
2. Keywords are extracted
3. Embedding model generates vector
4. SQL query retrieves candidate rows
5. Hybrid score is computed
6. Results are filtered and ranked
7. Snippet is extracted around keywords

## 7. Benefits of This Approach
* Works across multiple books and categories
* Balances semantic meaning and exact matches
* Prevents bias toward large books
* Provides readable snippets
* Scalable for large knowledge bases

## 8. Conclusion
This system is essentially the Retrieval component of a Retrieval-Augmented Generation (RAG) pipeline. It demonstrates how modern search engines combine embeddings with traditional full-text search to achieve accurate and user-friendly results.

## Setup Instructions
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file based on `.env.example` and fill in your PostgreSQL credentials.
3. Add your PDF files and modify `tools_insert.py` with the correct paths.
4. Run `python tools_insert.py` to index the books.
5. Run `python main.py` to start the search CLI.
