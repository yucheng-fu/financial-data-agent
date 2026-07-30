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
    user[User]
    fastapi[FastAPI Application]
    orchestrator[Agent Orchestrator]
    sql[SQL Agent]
    rag[RAG Agent]
    postgres[(PostgreSQL<br/>financials)]
    pgvector[(pgvector<br/>documents)]
    llm[LLM Response Generator]
    answer[User Answer]

    user -->|Natural language question| fastapi --> orchestrator
    orchestrator --> sql
    orchestrator --> rag
    sql --> postgres
    rag --> pgvector
    sql --> llm
    rag --> llm
    llm --> answer
```

## 4. Components

### FastAPI backend


## 5. Request Flow

## 6. Agent Orchestration

## 7. Tools and APIs

## 8. Data Model

## 9. Retrieval Strategy

## 10. MCP Integration

## 11. Deployment

## 12. Decisions and Tradeoffs
