# Financial Data Agent - Architecture

## 1. Overview
Financial Data Agent is an AI-powered assistant for analysing earnings reports for companies in the S&P 500.

The system combines three core capabilities:
- Structured financial data querying using SQL
- Semantic retrieval over financial documents using vector search
- Agent-based orchestration for selecting the appropriate tools


Primary use cases include:
- Financial metric lookup
- Earnings analysis
- Company comparisons
- Research question answering

## 3. High-level Architecture
```mermaid
flowchart TD
    user["User"]

    subgraph API["API Layer"]
        fastapi["FastAPI Backend"]
    end

    subgraph QueryPipeline["Agent / Query Processing"]
        orchestrator["Agent Orchestrator"]

        sql_tool["SQL Tool"]
        rag_tool["RAG Tool"]
        retrieval_tool["SEC acquisition Tool"]

        synthesizer["Large Language Model"]
    end

    subgraph IngestionPipeline["Data Ingestion Pipeline"]
        docs["Earnings Reports / SEC Filings"]
        extractor["Structured Data Extractor"]
        chunker["Text Chunker & Embedder"]
    end

    subgraph Storage["PostgreSQL Instance (Supabase)"]
        postgres[("Relational DB\n(Financial Metrics)")]
        pgvector[("pgvector\n(Document Embeddings)")]
    end

    %% =========================================================
    %% DATA INGESTION
    %% =========================================================

    docs -->|Extract Tables / Financials| extractor
    extractor -->|Insert Rows| postgres

    docs -->|Chunk & Embed Text| chunker
    chunker -->|Store Embeddings| pgvector

    %% =========================================================
    %% REQUEST / RESPONSE FLOW
    %% =========================================================

    user -->|1. Natural Language Question| fastapi
    fastapi -->|2. Route Query| orchestrator

    %% =========================================================
    %% AGENT TOOL SELECTION
    %% =========================================================

    orchestrator -->|3a. Structured Query| sql_tool
    orchestrator -->|3b. Document / Semantic Query| rag_tool
    orchestrator -->|3c. Missing Data / Filing Required| retrieval_tool

    %% =========================================================
    %% SQL TOOL
    %% =========================================================

    sql_tool -->|4a. Execute SQL| postgres
    postgres -->|5a. Return Rows / Financials| sql_tool

    %% =========================================================
    %% RAG TOOL
    %% =========================================================

    rag_tool -->|4b. Retrieve Relevant Chunks| pgvector
    pgvector -->|5b. Return Top-K Chunks| rag_tool

    %% =========================================================
    %% SEC ACQUISITION TOOL
    %% =========================================================

    retrieval_tool -->|4c. Fetch Earnings Reports / Filings| docs

    %% Retrieval populates the database
    retrieval_tool -->|Trigger Ingestion| extractor
    retrieval_tool -->|Trigger Chunking / Embedding| chunker

    %% =========================================================
    %% TOOL RESULTS → SYNTHESIS
    %% =========================================================

    sql_tool -->|6a. Structured Evidence| synthesizer
    rag_tool -->|6b. Document Evidence| synthesizer
    retrieval_tool -->|6c. Newly Retrieved Data| synthesizer

    %% =========================================================
    %% RESPONSE
    %% =========================================================

    synthesizer -->|7. Final Response| fastapi
    fastapi -->|8. HTTP Response| user
```

## 4. Components
### FastAPI backend
