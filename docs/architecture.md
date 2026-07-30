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

    subgraph QueryPipeline["Query Processing Pipeline"]
        orchestrator["Agent Orchestrator"]
        sql_agent["SQL Agent"]
        rag_agent["RAG Agent"]
        synthesizer["Large Language Model"]
    end

    subgraph IngestionPipeline["Data Ingestion Pipeline (Offline/Batch)"]
        docs["Earnings Reports (Documents)"]
        extractor["Structured Data Extractor"]
        chunker["Text Chunker & Embedder"]
    end

    subgraph Storage["PostgreSQL Instance"]
        postgres[("Relational DB\n(Financial Metrics)")]
        pgvector[("pgvector\n(Document Embeddings)")]
    end

    %% Ingestion Flow
    docs -->|Extract Tables / Financials| extractor -->|Insert Rows| postgres
    docs -->|Chunk & Embed Text| chunker -->|Store Embeddings| pgvector

    %% Request / Response Flow
    user -->|1. Natural Language Question| fastapi
    fastapi -->|2. Route Query| orchestrator

    orchestrator -->|3a. Structured Query| sql_agent
    orchestrator -->|3b. Semantic Search| rag_agent

    sql_agent -->|4a. Execute SQL| postgres
    postgres -->|5a. Return Rows / Financials| sql_agent

    rag_agent -->|4b. Similarity Search| pgvector
    pgvector -->|5b. Return Top-K Chunks| rag_agent

    sql_agent -->|6a. Structured Context| synthesizer
    rag_agent -->|6b. Unstructured Context| synthesizer

    synthesizer -->|7. Final Response| fastapi
    fastapi -->|8. HTTP Response| user
```

## 4. Components
### FastAPI backend
