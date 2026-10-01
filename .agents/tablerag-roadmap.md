# TableRAG Implementation Roadmap

Build order and settled design decisions for the agent layer described in `docs/architecture.md`, adapted from TableRAG (arXiv 2506.10380, `papers/TableRAG.pdf`).

This is a working document, not a design document. It records *what is left to do and why the decisions went the way they did*, so that each phase can be picked up independently without re-deriving the reasoning. Once a phase lands, its rationale moves into `docs/agent.md` and its entry here is reduced to a line.

## 1. How the design differs from the paper

TableRAG has an offline database-construction phase and an online four-step iterative reasoning loop: context-sensitive query decomposition, text retrieval, selective SQL execution, and compositional intermediate answer generation. Four deliberate deviations:

1. **No table-schema extraction, and no chunk→schema mapping.** The paper derives a relational schema per document because it cannot know what tables exist. Here the schema is fixed and permanent — `financial_metrics` joined to `documents` and `companies` — and fits in a prompt. The paper's mapping `f: chunk → S(D)` collapses into chunk metadata carrying `(ticker, year, quarter)`, which supplies the SQL tool's **filters** rather than its schema.
2. **An SEC acquisition tool the paper has no equivalent for.** TableRAG assumes a closed corpus. Here a question can discover its data is missing, fetch the filing, ingest it, and retry — a write path into the store at query time (see deviation 4 for where that decision sits).
3. **Query decomposition and retry are kept in full.** This is the part of the paper that earns its keep for questions like "compare AAPL and MSFT operating margin over three years", which a single routing decision cannot serve.
4. **Acquisition lives in the chat agent, not in the TableRAG loop.** TableRAG runs as a LangGraph subgraph behind the `table_rag` tool, and a chat graph above it decides when to call `acquire_filing`. When retrieval and SQL both come back empty for a `(ticker, year, quarter)`, the subgraph reports the gap; the chat agent acquires and retries. This deletes the per-subquery `acquired` latch — the global acquisition budget becomes a counter in chat state, checked by the tool wrapper.

Consequently `route_sql` replaces the paper's "are there table chunks in the top-N?" test with the equivalent for a fixed schema: run SQL if any reranked chunk has `is_table = true`, **or** the subquery names a metric in `METRIC_FIELDS`.

## 2. Settled decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Vector store | Own `DocumentChunk` model and a hand-written migration | `docs/database.md` makes `migrations/versions/` the single source of truth. `langchain-postgres` creates its own tables outside Alembic and filters through a JSONB blob instead of real columns and foreign keys |
| Embedding backend | `fastembed` running `BAAI/bge-small-en-v1.5` on onnxruntime, in process, as a core dependency | Free, no API key, no rate limit, ~150MB added to the image. The same weights serve the offline import and online queries, so corpus and query vectors cannot drift apart. Deliberately not sentence-transformers, which pulls in torch. One backend means no provider registry and no optional extras |
| Embedding dimension | Fixed at 384 in the DDL; model name configurable | pgvector needs a literal dimension for HNSW to be creatable at all, and a migration that reads `os.getenv` at apply time is schema drift by construction. Raising it later is a migration plus a full re-embed, and the eval harness should be what decides it |
| Index | HNSW, `vector_cosine_ops` | IVFFlat's lists are k-means centroids over current contents, so building it on an empty table yields a degenerate index that must be rebuilt after ingestion. HNSW is correct on an empty table and stays correct as the acquisition tool appends |
| Chat backend | langchain-core `BaseChatModel` seam; an external hosted API with a free tier; provider chosen by the eval harness from candidates such as the Gemini API, Groq and GitHub Models | The evaluation harness exists to answer which provider; pre-committing makes its main axis a constant. `BaseChatModel` is already transitive via `langchain-text-splitters` and is what LangGraph's `bind_tools` needs. The provider must support tool calling. No Azure AI Foundry or Azure OpenAI: neither is free, and an external API needs only one more Container App secret |
| Deployment split | Embeddings in process everywhere; a hosted API for the chat model only | A 33M-parameter embedding model fits the Container App's 0.5 CPU / 1Gi profile. A 7–8B chat model does not, at any Consumption size, and generates autoregressively over five-plus calls per question — that is the part that has to be hosted |
| Orchestration | LangGraph: a chat graph (`MessagesState`, `agent` ↔ `ToolNode`) over a TableRAG subgraph | Reverses the earlier hand-rolled dispatch loop. The chat layer needs tool calling, multi-turn history and a step bound, which `bind_tools`, `ToolNode`, `tools_condition` and `recursion_limit` provide directly; re-implementing them on top of the TableRAG loop would be the larger codebase. Nodes stay module-level callables because AGENTS.md forbids nested functions |
| Tool location | `api/tools/`, thin wrappers over services, like `api/v1` routes | Tools are an API surface (in-process and MCP), so they sit beside the routes and keep `agent/` free of `api/` imports. Services stay the only home of business logic |
| Conversation state | Own `conversations` and `conversation_messages` tables, hand-written migration; no LangGraph checkpointer | `langgraph-checkpoint-postgres` creates its own tables outside Alembic — the same reason `langchain-postgres` was rejected. Only user messages and final answers are stored; tool calls go in a JSONB `trace`, keeping replayed context bounded |
| Reranking | LLM listwise behind a `Reranker` Protocol, with a BM25 + reciprocal-rank-fusion baseline beside it | The paper uses a BGE cross-encoder via `sentence-transformers`, which pulls in torch — a far heavier image than onnxruntime for the same job. Worth revisiting: fastembed also ships ONNX cross-encoder rerankers, which would match the paper without torch. BM25 stays as the dependency-free baseline that proves whether reranking earns its latency at all |
| MCP | Built: `FastMCP` with `stateless_http=True`, mounted at `/mcp` in `api/main.py`, same image and Container App | The same `api/tools` functions are registered on the MCP server and bound in process via `StructuredTool.from_function`, so the app's own agent takes no MCP hop. Tools wrap **services**, not the app's own HTTP routes. A separate MCP Container App was rejected: a second deployment, a network hop and inter-app auth, with no scaling benefit at `max_replicas = 1` |
| Demo front end | GitHub Pages | A static CDN never sleeps, so the portfolio link is always instant, and it adds no platform the project does not already use. A Gradio Space sleeps; a model-hosting Space sleeps *and* is CPU-only |

### The provider seam

No module in `agent/`, `services/` or `evaluation/` may import a provider package. They accept the `Embedder` Protocol and a langchain-core `BaseChatModel`, and nothing more.

- **`Embedder`** lives in `ingestion/embeddings.py` and is implemented once, by `OnnxEmbedder`. Two methods, `embed_documents` and `embed_query`.
- **`BaseChatModel`** replaces the planned `TextGenerator` Protocol. `ingestion/llm.py` `build_chat_model()` constructs it from `LLM_PROVIDER` and `LLM_MODEL`. Construction belongs in `ingestion/`, which AGENTS.md defines as "External I/O only" — an LLM client is exactly that — and the provider package (e.g. `langchain-google-genai`, `langchain-groq`) is imported inside the branch that needs it, the pattern `build_data_storage()` already uses for the Azure SDK.
- **Structured output is parsed, not delegated.** The TableRAG decompose contract is plain JSON, and `agent/parsing.py` extracts it from a fenced or bare response. Providers that can constrain decoding should, but the parser must not assume it. The chat graph uses native tool calling, so the provider must support it.
- **`LLM_PROVIDER`, `LLM_MODEL` and `EMBEDDING_MODEL` use `require_env` with no default.** For a project whose point is benchmarking, silently defaulting to some model is worse than a `RuntimeError`.
- **Treat an embedding model change as a re-embed.** The same model at different quantizations produces different vectors, so embedding the corpus with one and querying with another silently degrades retrieval — nothing errors, results just get worse. Running the same in-process model on both sides avoids this entirely, which is the main reason it is not configurable per environment.

### Deployment note for the embedding model

`fastembed` downloads the model to a cache directory on first use, defaulting to a temporary directory. That is fine locally but wrong in a container, which would re-download on every cold start and take a network dependency at startup. Phase 12 should bake the model into the image at build time and set `EMBEDDING_CACHE_DIR` to that path.

## 3. Traps in the existing code

Each turns an obvious implementation into a wrong one. Verified by inspection.

1. **`raw_document_path` is not a portable storage key.** `LocalDataStorage.save_text` returns an absolute path (`storage.py:84`); `AzureBlobDataStorage` returns the bare blob name (`storage.py:148`). Reading it back through `read_text()` works in one environment and breaks in the other. Re-derive with `filing_blob_name(company.ticker, document.year, document.quarter)`, deterministic because `FilingImportService` passes the same triple to both `fetch_filing` and the `Document`.
2. **`Company.CIK` is a quoted, case-sensitive Postgres column** (`"CIK" VARCHAR(255)`). NL2SQL emitting `SELECT cik FROM companies` fails. The schema prompt must show it quoted, and a test must assert the quoting survives prompt edits.
3. **`financial_metrics.period` is `"Q1"` but `documents.quarter` is `2`.** Without an explicit instruction the model emits `WHERE period = 2`. The schema prompt must say to filter on `documents.quarter` and join.
4. **The autouse `stub_db_session` fixture in `tests/conftest.py` replaces `get_session` with `MagicMock(spec=Session)`.** A MagicMock returns Mock objects from `session.execute(...)`, so an agent route test would pass while asserting nothing. Agent route tests must override it with a real SQLite session.
5. **Both graphs need a hard step bound, and acquisition needs its own budget.** A routing bug can cycle between nodes, and a model can keep calling `acquire_filing`. Pass `recursion_limit` on every invoke of the chat graph and the TableRAG subgraph, derived from the configured bounds, so a run raises rather than spins. The per-request acquisition counter lives in chat state and the `acquire_filing` wrapper refuses once it is spent — `recursion_limit` alone would allow several SEC round-trips before tripping.
6. **`alembic revision --autogenerate` produces a broken migration for `Vector` columns** — it emits the type without the import, never emits `CREATE EXTENSION`, and on later autogenerates tries to drop the HNSW index it cannot model. Write vector migrations by hand and add an `include_object` hook to `migrations/env.py`.
7. **A mounted FastMCP app needs its session manager running.** Mounting `mcp.streamable_http_app()` in `api/main.py` is not enough: the FastAPI `lifespan` must enter `mcp.session_manager.run()`, or the first `/mcp` request fails. `TestClient` only runs the lifespan when used as a context manager, so the MCP test must use `with TestClient(app) as client`.
8. **Model-generated SQL must not run as the main user.** A read-only transaction blocks writes but not reads, so once `conversations` exist (Phase 9) the model could read other users' messages. It runs as the `llm_reader` role instead, with `SELECT` on `companies`, `documents` and `financial_metrics` only — a separate login, hence a separate small engine. `SET LOCAL ROLE` on the main connection was rejected: a query can switch back from inside a `SELECT`.
9. **`/mcp` is on public ingress.** The Container App exposes one ingress, so mounting `/mcp` publishes every tool — including `acquire_filing`, a write path into blob storage and Supabase. Require a bearer token matching `MCP_API_KEY` before the mount ships, and test that a request without it is rejected.

## 4. Phases

Each phase leaves the repo green under `uv run ruff check . && uv run ruff format --check . && uv run pyrefly check && uv run pytest`, and each is independently mergeable.

| # | Phase | Status | Adds dependencies |
| --- | --- | --- | --- |
| 1 | Storage read path | done | no |
| 2 | Chunk schema and migration | done | no |
| 3 | Table-aware markdown chunking | done | `langchain-text-splitters` |
| 4 | Chunk import service and route | done | `fastembed` |
| 5 | Read-only SQL execution | done | no |
| 6 | TableRAG scaffolding | not started | no |
| 7 | TableRAG nodes and subgraph | not started | `langgraph` |
| 8 | Tools and MCP mount | not started | `mcp` |
| 9 | Conversation store | not started | no |
| 10 | Chat graph and route | not started | no |
| 11 | Evaluation harness | not started | candidate provider packages |
| 12 | Deployed inference and front end | not started | the chosen provider package |
| 13 | Documentation | not started | no |

Phases 1–4 are done. Phases 5–13 follow.

### Phase 5 — Read-only SQL execution

Done. Migration `4f1a9c3e7b2d` creates the `llm_reader` role (trap 8); `get_llm_reader_engine()` in `db/database.py` logs in as it from `LLM_READER_DATABASE_URL`; `services/sql_query.py` `execute_llm_sql` runs the SQL with `SET LOCAL statement_timeout`, `fetchmany(row_limit + 1)` and `finally: session.rollback()`. No regex guard: the role's grants are the enforcement, and Postgres' `permission denied` is the error the model sees. The permission tests in `tests/test_sql_query.py` need a reachable `LLM_READER_DATABASE_URL` and skip without one, including in CI.

Known gap: the SQL is sent without parameters, so psycopg allows several statements, and `SET statement_timeout = 0; SELECT pg_sleep(...)` overrides the timeout. The pool is capped at two connections, so the damage is bounded; close it in Phase 12 before the endpoint goes public.

### Phase 6 — TableRAG scaffolding, no graph

`agent/tablerag/{constants,errors,schema,state,parsing,rerank,routing}.py` and `services/chunk_retrieval.py`. Every file is a pure function or a thin protocol, testable with no graph and no I/O.

`agent/tablerag/state.py` holds the subgraph state as a `TypedDict`, with `Annotated[list[...], operator.add]` reducers on the accumulators (`history`, `citations`, `errors`), so nodes return **deltas** and never rebuild a list. `iteration` and `max_iterations` live in state, not module constants, so routers stay pure and tests can set `max_iterations=2` without monkeypatching. There is no `acquired` latch and no acquisition counter here — see §1 deviation 4.

`agent/tablerag/schema.py` generates the schema prompt from `METRIC_FIELDS` so it cannot drift from the model, and encodes traps 2 and 3.

`agent/tablerag/rerank.py` holds BM25 and reciprocal rank fusion in about thirty lines of stdlib. Do not add `rank-bm25`: it imports numpy at module scope, and numpy is not a declared dependency of this project.

Also add `search_similar` to `DocumentChunkRepository`, split into a pure `build_search_statement(...)` and a thin executor. It must compile to the `<=>` **operator** — `func.cosine_distance(...)` does not use the HNSW index and silently turns every query into a sequential scan. Test the compiled SQL, since SQLite cannot run `<=>`.

### Phase 7 — TableRAG nodes and subgraph

`agent/tablerag/prompts/` transcribing the paper's Appendix G templates. The decomposition prompt loses `{table_content}` and gains the subquery-answer history plus the fixed schema; the intermediate-answer prompt keeps its cross-validation instructions close to verbatim — prefer SQL on conflict, fall back to text when SQL errored, explain discrepancies.

`agent/tablerag/nodes/*.py`, one module-level callable per node, with the chat model, embedder and session bound when the graph is built. Each is testable on its own against a hand-built state dict, before any graph exists.

The decompose contract is one of two JSON shapes:

```json
{"action": "subquery", "subquery": "...", "tickers": ["AAPL"], "years": [2024], "quarters": [3]}
{"action": "answer"}
```

This keeps the subgraph independent of native tool calling and hands `retrieve` its filters for free.

`agent/tablerag/graph.py` — `build_tablerag_graph(session, chat_model, embedder, ...)` compiles the `StateGraph` (`decompose → retrieve → rerank → (route_sql) sql → intermediate_answer → decompose … → finalize`), with both backends injected and never constructed here; that injection is what lets the eval harness swap them. Built per request, which keeps the session lifetime scoped to the request.

When retrieval and SQL are both empty for a subquery's `(ticker, year, quarter)`, `intermediate_answer` records a `missing` entry and `finalize` returns it alongside the answer, so the chat agent can decide to acquire.

The graph test asserts the **visit sequence**, not just the final answer — a final-answer assertion alone passes even if `route_sql` never fired. A second test asserts a subquery with no data surfaces in `missing`.

### Phase 8 — Tools and MCP mount

`api/tools/` with one module per tool, each a thin wrapper that calls services and translates service exceptions into tool errors:

- `table_rag(question, tickers?, years?, quarters?)` — builds and invokes the TableRAG subgraph; returns answer, citations, `steps` and `missing`.
- `list_available_filings(ticker?)` — a new read on `DocumentRepository` returning `(ticker, year, quarter)` with chunk counts, so the agent knows coverage before answering.
- `acquire_filing(ticker, year, quarter)` — runs `FilingImportService`, `FinancialMetricsImportService` and `DocumentChunkImportService` in order. When the filing is already stored but has no chunks, it only re-chunks from the blob. Checks the acquisition budget (trap 5).

`api/tools/mcp_server.py` registers the same functions on a `FastMCP` server with `stateless_http=True`; `api/main.py` mounts `streamable_http_app()` at `/mcp` and runs the session manager in `lifespan` (trap 7), behind the `MCP_API_KEY` bearer check (trap 9). Over MCP each call opens its own session from `get_session_factory()`; in process the chat graph passes the request's session.

Tests call each tool function directly with fakes patched on the service modules, plus one `/mcp` test for the lifespan and one for the missing-token rejection.

### Phase 9 — Conversation store

`db/models/conversation.py` with `Conversation` and `ConversationMessage` (pattern: `db/models/document_chunk.py`, `TimestampMixin`), exported from `db/models/__init__.py`, and a hand-written migration following `7d4e2c81f9a3_document_chunks.py`:

- `conversations`: `id` UUID PK with server default `gen_random_uuid()`, `title` VARCHAR(255) null, timestamps.
- `conversation_messages`: `id` PK, `conversation_id` FK `ON DELETE CASCADE`, `position` INT, `role` VARCHAR(20) with CHECK `role IN ('user', 'assistant')`, `content` TEXT, `trace` JSONB null, timestamps; `UNIQUE (conversation_id, position)`.
- Both tables: `ENABLE ROW LEVEL SECURITY` in the same migration, with no policies. Supabase grants `anon` full access to every new `public` table through its REST API, and RLS is what closes it (see `9a2e6d4b1c8f`). Do not grant them to `llm_reader`.

`ConversationRepository` with `create`, `get_messages` and `append_message`. Verify with `alembic upgrade head`, `downgrade -1`, `upgrade head`, then `alembic check` reports no drift.

### Phase 10 — Chat graph and route

`agent/chat_graph.py` — `build_chat_graph(chat_model, tools)` compiles a `StateGraph` over `MessagesState`: an `agent` node calling `chat_model.bind_tools(tools)`, a `ToolNode`, and `tools_condition`. No checkpointer. Invoked with `recursion_limit` (trap 5).

`services/chat.py` — loads history from `ConversationRepository`, converts it to messages, invokes the graph, and appends the user message and the final assistant answer with citations and `steps` in `trace`.

Routes `POST /api/v1/chat` (`{conversation_id?, message}` → `{conversation_id, answer, citations, steps}`) and `GET /api/v1/conversations/{id}`, sync `def` like every existing route — the persistence stack is sync SQLAlchemy, and FastAPI already runs sync routes in a threadpool. Tools are bound in process via `StructuredTool.from_function`.

Document the concurrency ceiling: a 30–120s run occupies one of anyio's 40 threadpool workers against `max_replicas = 1`, so the answer to throughput later is `202 Accepted` plus a job table, not async/await.

Tests use a `GenericFakeChatModel` subclass that overrides `bind_tools` to return `self` (the stock fake raises), with scripted `AIMessage`s carrying `tool_calls`. Assert a follow-up question is answered from history with no tool call, and that a missing filing leads to exactly one `acquire_filing` call.

### Phase 11 — Evaluation harness

Code in `src/financial_data_agent/evaluation/` so ruff, pyrefly and the import path treat it like the rest of the package; data and results in `evals/` at the repo root. Add `evals` to `.dockerignore`.

- `dataset.py` — JSONL records `{id, question, answer, answer_type, source, scope, gold_sql, hops, tags}`, where `source ∈ {sql, text, both}` mirrors the paper's single-source/multi-source split.
- `generate.py` — builds the metric half **deterministically** from `financial_metrics` rows via templates, gold answers read straight from the database. This is where the project is better off than the paper, which needed two human annotators per answer. The narrative half is LLM-drafted from chunks for manual review.
- `metrics.py` — `numeric_match` with tolerance and `exact_match` (no judge, free, reproducible), `sql_execution_match` comparing result sets against `gold_sql`, `retrieval_hit_rate`, plus `iterations`, `terminated_at_max` (the paper's "refusal or exceeding max iteration" bucket) and per-step latency.
- `judge.py` — the paper's binary 0/1 evaluation prompt (Appendix G), narrative answers only, judge model and provider pinned independently of the model under test.
- `run.py` — `--provider` and `--model` are first-class axes, so *which backend to adopt* is an output of the harness rather than an input to the design. Candidates are external APIs with a free tier and tool calling (the Gemini API, Groq, GitHub Models); record each tier's rate limits and data terms alongside the scores. `--no-decomposition`, `--no-sql`, `--no-retrieval` reproduce the paper's Figure 4 ablations; `--reranker bm25|llm|none` settles the reranking question on evidence.
- `compare.py` — a markdown table across runs, refusing to compare runs whose judge model, embedding model or dataset hash differ.

### Phase 12 — Deployed inference and the front end

The chat model is the external hosted API chosen in Phase 11 — no Azure AI Foundry, no Azure OpenAI, no self-hosting. Wire it into the deployed path: its API key and `MCP_API_KEY` as Terraform secrets alongside `database-url` in `iac/environments/{test,prod}/main.tf`, following the existing `secrets` / `secret_env_vars` pattern, plus `LLM_PROVIDER` and `LLM_MODEL` as plain `env_vars`. The container-app module needs no changes — it already iterates secret names generically. Also wire `LLM_READER_DATABASE_URL`: a `llm_reader_db_password` Terraform variable, the URL composed in the Supabase module with the pooler username `llm_reader.<project-ref>`, and an `ALTER ROLE llm_reader LOGIN PASSWORD` step after `alembic upgrade head` in each migrate job.

The front end is **GitHub Pages**: a static page calling `POST /api/v1/chat` from the visitor's browser and rendering the conversation plus the `steps` trace. Source in a `demo/` directory, published by a new job in the existing workflow. **Do not use the "deploy from `/docs`" Pages option** — `docs/` holds the design documents and Pages would publish those. Add `demo` to `.dockerignore`.

This means the app needs CORS, which it has never had: `CORSMiddleware` in `api/main.py` allowing the Pages origin specifically, never `*`, with the origin read from config so local development can allow `localhost`.

Confirm before closing the phase: the Container App scales to zero, so the first request after idle pays a *container* cold start even though the inference API does not — decide whether that is acceptable or whether `min_replicas` should be 1. The demo endpoint is public and every request spends the provider's free-tier quota, so decide on a rate limit. And `/docs` is public too, which is fine but worth a deliberate look before the link goes on a CV.

### Phase 13 — Documentation

- `docs/architecture.md` is already rewritten for this design; update it only where implementation diverged.
- `docs/agent.md` — why schema retrieval was dropped, how `route_sql` replaces the table-chunk trigger, why acquisition moved to the chat agent and how its budget works, HNSW versus IVFFlat, the read-only SQL threat model and the least-privilege-role recommendation, the `BaseChatModel` seam and how to add a provider, why LangGraph replaced the hand-rolled loop, why conversations are not checkpointed, why embeddings run in process while the chat model is hosted, and the MCP mount with the separate-app alternative stated and rejected.
- `docs/evaluation.md` — dataset format, metric definitions, how to add a model or provider, and what invalidates a cross-run comparison.
- `docs/infrastructure.md` — the inference API key and `MCP_API_KEY` joining `database-url` in the secret-provenance table, the Pages front end as a component Terraform does not own, and the Pages deploy job in the pipeline walkthrough. While here, fix the stale line at `infrastructure.md:85` claiming `az acr build` builds the image; the workflow uses `docker/build-push-action` with buildx.
- `README.md`, `agent/README.md`, `evals/README.md` — commands only, under 50 lines, each ending in a `## Further reading` link.
- `AGENTS.md` — the folder tree with `agent/`, `agent/tablerag/` and `api/tools/`, the `api → agent → services` layering line, and one new rule: read-model dataclasses returned by repositories may be imported by the layers above.

## 5. Dependency rules

Pin exactly rather than by range: this is a benchmarking harness, and a silent minor bump that changes prompt formatting or structured-output behaviour invalidates recorded numbers.

Chunking uses `langchain-text-splitters`, which brings `langchain-core` and `langsmith`. Orchestration uses `langgraph` (Phase 7) and MCP uses `mcp` (Phase 8). Embeddings are `fastembed` on onnxruntime. The chat backend is one LangChain provider package (e.g. `langchain-google-genai`, `langchain-groq`) behind `BaseChatModel`, imported inside the branch of `build_chat_model()` that builds it.

Do not add:

- `langchain`, `langchain-community`, `langgraph-checkpoint-postgres` — the first two are framework dependency trees nothing here needs; the checkpointer creates tables outside Alembic.
- `sentence-transformers`, `transformers`, `FlagEmbedding` — each drags in roughly 2.5GB of torch, past the 1Gi container limit. This is why the fallback reranker is BM25.
- `tiktoken` — downloads encoding files from a CDN on first use, a runtime network call in a container with no egress guarantee. `len(text) // 4` is sufficient for chunk sizing.
- `rank-bm25` — imports numpy at module scope, and numpy is not a declared dependency of this project.

When a chat provider package is added, check what telemetry it ships with and disable it explicitly in the Dockerfile `ENV` block — including LangSmith tracing, which `langchain-core` enables from environment variables. Filing text should not leave the container by default.

Free tiers may use prompts for training. Filings are public, but user messages are not, so the chosen tier's data terms are part of the provider decision in Phase 11, not an afterthought.

## 6. Testing notes

Follow the three patterns already in `tests/`: monkeypatch the imported name in the *service* module; a real in-memory SQLite session plus `app.dependency_overrides` for repository round-trips; hand-written fakes for external I/O.

`uv run pytest` must pass **with no provider package installed** — that is what proves the seam holds.

A `GenericFakeChatModel` subclass with scripted responses (overriding `bind_tools` to return `self`) and a `FakeEmbedder` returning deterministic vectors keep graph tests free of network and of any provider. Derive the fake's vector index with `zlib.crc32`, **not** `hash()`: Python's string hash is salted per process, giving a test that passes locally and fails one CI run in three.

## 7. Chunking

`MarkdownHeaderTextSplitter` cuts sections on headings, `RecursiveCharacterTextSplitter` splits the prose inside them, and table blocks are routed around the recursive splitter entirely.

That last part is not optional. `RecursiveCharacterTextSplitter` separates on `["

", "
", " ", ""]`, so a table longer than `chunk_size` is cut between rows: measured on a 60-row table at `chunk_size=400`, it produced five pieces of which one retained the header row. The other four are columns of numbers with nothing naming them. This is the failure the paper opens with, and `is_table` is what `route_sql` keys on in Phase 6, so a chunk that is half a table is wrong twice over.

`char_start` / `char_end` were dropped when chunking moved to these splitters. `MarkdownHeaderTextSplitter` rejoins lines with `"  
"` and both splitters strip, so chunk content is not a verbatim substring of the source and the offsets could not be recovered honestly. Citations use `accession_number`, `chunk_index` and `heading_path` instead.

Token counts remain a `len(text) // 4` heuristic, and `RecursiveCharacterTextSplitter` is given `max_tokens * 4` characters. Both are approximate, and dense numeric tables tokenize worse than the heuristic suggests.
