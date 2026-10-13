# Financial Data Agent - TableRAG

## 1. Components
`agent/tablerag/graph.py` `build_tablerag_graph(session, reader_session, chat_model, embedder)` compiles the subgraph. The caller constructs every backend and injects it; the graph never builds one. Each node is a module-level function in `agent/tablerag/nodes/`, bound to its backends with `functools.partial`.

```mermaid
flowchart TD
    caller["Caller\n(table_rag tool, eval harness)"]

    subgraph Agent["agent/tablerag"]
        builder["graph.py\nbuild_tablerag_graph"]
        state[("state.py\nTableRAGState")]

        subgraph Nodes["nodes/"]
            decompose["decompose"]
            retrieve["retrieve"]
            rerank_node["rerank"]
            sql["sql"]
            intermediate["intermediate_answer"]
        end

        prompts["prompts.py\nAppendix G templates"]
        parsing["parsing.py\nJSON contract"]
        rerank["rerank.py\nBM25 + RRF"]
        routing["routing.py\nroute_after_decompose\nroute_sql"]
        schema["agent/schema.py\nbuild_schema_prompt"]
    end

    subgraph Services["services/"]
        chunk_retrieval["chunk_retrieval.py\nretrieve_chunks"]
        sql_query["sql_query.py\nexecute_llm_sql"]
    end

    repo["DocumentChunkRepository\nsearch_similar"]
    llm["Chat model\n(BaseChatModel)"]
    embedder["Embedder\n(fastembed)"]

    subgraph Postgres["PostgreSQL"]
        chunks[("document_chunks\n(pgvector, HNSW)")]
        metrics[("companies, documents\nfinancial_metrics")]
    end

    caller -->|"session, reader_session,\nchat_model, embedder"| builder
    builder -->|binds| Nodes
    builder -->|conditional edges| routing
    Nodes <-->|read state / return deltas| state

    decompose --> prompts
    decompose --> schema
    decompose --> parsing
    decompose <--> llm

    retrieve --> chunk_retrieval
    chunk_retrieval -->|embed_query| embedder
    chunk_retrieval --> repo
    repo -->|"ORDER BY embedding <=> query"| chunks

    rerank_node --> rerank

    sql --> sql_query
    sql_query -->|"as llm_reader"| metrics

    intermediate --> prompts
    intermediate --> schema
    intermediate <--> llm
```

- **Two sessions.** `retrieve` searches chunks on the main session, because `document_chunks` is not granted to `llm_reader`. `sql` runs model-generated SQL on the `llm_reader` session only.
- **Provider seam.** Nodes see only `BaseChatModel` and the `Embedder` Protocol. No module in `agent/` imports a provider package.

## 2. Control Flow

```mermaid
flowchart LR
    start(["START"])
    decompose["decompose"]
    retrieve["retrieve"]
    rerank["rerank"]
    sql["sql"]
    intermediate["intermediate_answer"]
    finish(["END"])

    start --> decompose
    decompose -->|subquery| retrieve
    decompose -->|"answer, or past max_iterations"| finish
    retrieve -->|top RETRIEVE_TOP_K| rerank
    rerank -->|"route_sql: SQL written and\n(table chunk or metric named)"| sql
    rerank -->|otherwise| intermediate
    sql --> intermediate
    intermediate --> decompose
```

| Node | Reads | Writes | Model call |
| --- | --- | --- | --- |
| `decompose` | `question`, `history`, `iteration` | `current`, `iteration + 1`, clears `sql_result`/`sql_error`; or `answer` | yes |
| `retrieve` | `current` (subquery, filters) | `candidates` | no |
| `rerank` | `current`, `candidates` | `reranked` (top `RERANK_TOP_K`) | no |
| `sql` | `current.sql` | `sql_result`, or `sql_error` and `errors` | no |
| `intermediate_answer` | `current`, `reranked`, `candidates`, `sql_result`, `sql_error` | `history`, `citations`, `missing` | yes |

With `MAX_ITERATIONS = 2` a question costs at most five model calls: two per subquery, plus the final decompose. Folding SQL generation into decompose is what keeps it at five; the paper's separate NL2SQL call would make it seven.

## 3. One Question, End to End

```mermaid
sequenceDiagram
    participant C as Caller
    participant G as Subgraph
    participant M as Chat model
    participant V as document_chunks
    participant R as financial_metrics (llm_reader)

    C->>G: initial_state(question), recursion_limit_for(max_iterations)
    G->>M: decompose prompt (schema, history)
    M-->>G: {"action": "subquery", tickers, years, quarters, sql}
    G->>V: similarity search with filters
    V-->>G: candidates
    Note over G: BM25 + RRF rerank, then route_sql
    G->>R: sql (if routed)
    R-->>G: rows or error
    G->>M: intermediate answer prompt (passages, SQL, result)
    M-->>G: subquery answer
    Note over G: history, citations, missing += ...
    G->>M: decompose prompt (with history)
    M-->>G: {"action": "answer", "answer": "..."}
    G-->>C: answer, history, citations, missing, errors
```

## 4. Contracts and Bounds
- **Decompose reply.** Exactly one JSON object, fenced or bare: `{"action": "subquery", "subquery", "tickers", "years", "quarters", "sql": "..." | null}` or `{"action": "answer", "answer": "..."}`. Anything else raises `DecompositionParseError`; there is no retry, because a retry spends the daily request budget.
- **State updates.** Nodes return deltas. `history` and `errors` append; `citations` and `missing` append only unseen items.
- **Step bound.** Every invoke passes `recursion_limit_for(max_iterations)` = `5 * max_iterations + 2`. If the model still asks for a subquery past `max_iterations`, the graph ends with `answer = None`.
- **SQL errors** are recorded, not raised, so the intermediate answer falls back to the passages.
- **Missing filings.** A fully named `(ticker, year, quarter)` absent from the candidates, when SQL returned no rows, is reported in `missing`. The subgraph never acquires; the chat agent decides whether to call `acquire_filing`.
