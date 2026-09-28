# TableRAG Implementation Roadmap

Build order and settled design decisions for the agent layer described in `docs/architecture.md`, adapted from TableRAG (arXiv 2506.10380, `papers/TableRAG.pdf`).

This is a working document, not a design document. It records *what is left to do and why the decisions went the way they did*, so that each phase can be picked up independently without re-deriving the reasoning. Once a phase lands, its rationale moves into `docs/agent.md` and its entry here is reduced to a line.

## 1. How the design differs from the paper

TableRAG has an offline database-construction phase and an online four-step iterative reasoning loop: context-sensitive query decomposition, text retrieval, selective SQL execution, and compositional intermediate answer generation. Three deliberate deviations:

1. **No table-schema extraction, and no chunk→schema mapping.** The paper derives a relational schema per document because it cannot know what tables exist. Here the schema is fixed and permanent — `financial_metrics` joined to `documents` and `companies` — and fits in a prompt. The paper's mapping `f: chunk → S(D)` collapses into chunk metadata carrying `(ticker, year, quarter)`, which supplies the SQL tool's **filters** rather than its schema.
2. **An SEC acquisition tool the paper has no equivalent for.** TableRAG assumes a closed corpus. Here a subquery can discover its data is missing, fetch the filing, ingest it, and retry — a write path into the store at query time.
3. **Query decomposition and retry are kept in full.** This is the part of the paper that earns its keep for questions like "compare AAPL and MSFT operating margin over three years", which a single routing decision cannot serve.

Consequently `route_sql` replaces the paper's "are there table chunks in the top-N?" test with the equivalent for a fixed schema: run SQL if any reranked chunk has `is_table = true`, **or** the subquery names a metric in `METRIC_FIELDS`.

## 2. Settled decisions

| Decision | Choice | Reason |
| --- | --- | --- |
| Vector store | Own `DocumentChunk` model and a hand-written migration | `docs/database.md` makes `migrations/versions/` the single source of truth. `langchain-postgres` creates its own tables outside Alembic and filters through a JSONB blob instead of real columns and foreign keys |
| Embedding backend | `fastembed` running `BAAI/bge-small-en-v1.5` on onnxruntime, in process, as a core dependency | Free, no API key, no rate limit, ~150MB added to the image. The same weights serve the offline import and online queries, so corpus and query vectors cannot drift apart. Deliberately not sentence-transformers, which pulls in torch. One backend means no provider registry and no optional extras |
| Embedding dimension | Fixed at 384 in the DDL; model name configurable | pgvector needs a literal dimension for HNSW to be creatable at all, and a migration that reads `os.getenv` at apply time is schema drift by construction. Raising it later is a migration plus a full re-embed, and the eval harness should be what decides it |
| Index | HNSW, `vector_cosine_ops` | IVFFlat's lists are k-means centroids over current contents, so building it on an empty table yields a degenerate index that must be rebuilt after ingestion. HNSW is correct on an empty table and stays correct as the acquisition tool appends |
| Chat backend | Deferred. Code is written against a local `TextGenerator` Protocol | The evaluation harness exists to answer this question; pre-committing makes its main axis a constant. The Protocol is two methods, so an adapter for any provider is a few lines and the project takes no framework dependency to get one |
| Deployment split | Embeddings in process everywhere; a hosted API for the chat model only | A 33M-parameter embedding model fits the Container App's 0.5 CPU / 1Gi profile. A 7–8B chat model does not, at any Consumption size, and generates autoregressively over five-plus calls per question — that is the part that has to be hosted |
| Orchestration | Hand-rolled state machine, nodes as **callable classes** | The graph is seven nodes and three conditional edges — a dispatch loop over a frozen state dataclass, on the order of a hundred lines. LangGraph was considered and dropped: the project takes no LangChain dependency, and a framework whose main value here is `add_conditional_edges` does not earn a dependency tree. Callable classes rather than closures because AGENTS.md forbids nested functions |
| Reranking | LLM listwise behind a `Reranker` Protocol, with a BM25 + reciprocal-rank-fusion baseline beside it | The paper uses a BGE cross-encoder via `sentence-transformers`, which pulls in torch — a far heavier image than onnxruntime for the same job. Worth revisiting: fastembed also ships ONNX cross-encoder rerankers, which would match the paper without torch. BM25 stays as the dependency-free baseline that proves whether reranking earns its latency at all |
| MCP | Documented, not built | The agent is in-process with its tools; MCP would be `agent → client → transport → server → the same function`. Its tools wrap **services**, not the app's own HTTP routes. Revisit when an external client (Claude Desktop, an IDE) needs to query this data |
| Demo front end | GitHub Pages | A static CDN never sleeps, so the portfolio link is always instant, and it adds no platform the project does not already use. A Gradio Space sleeps; a model-hosting Space sleeps *and* is CPU-only |

### The provider seam

No module in `agent/`, `services/` or `evaluation/` may import a provider SDK. They accept the two Protocols defined in `ingestion/` and nothing more.

- **`Embedder`** lives in `ingestion/embeddings.py` and is implemented once, by `OnnxEmbedder`. Two methods, `embed_documents` and `embed_query`.
- **`TextGenerator`** will live in `ingestion/llm.py` when Phase 6 lands: `generate(system_prompt, user_prompt)` and `generate_json(...)`. Construction belongs in `ingestion/`, which AGENTS.md defines as "External I/O only" — an LLM client is exactly that — and the provider SDK is imported inside the branch that needs it, the pattern `build_data_storage()` already uses for the Azure SDK.
- **Structured output is parsed, not delegated.** With no framework `with_structured_output()`, `agent/parsing.py` extracts JSON from a fenced or bare response. Adapters that can constrain decoding should do so (an Ollama-style `format="json"`, a hosted provider's JSON mode), but the parser must not assume it.
- **`LLM_MODEL` and `EMBEDDING_MODEL` use `require_env` with no default.** For a project whose point is benchmarking, silently defaulting to some model is worse than a `RuntimeError`.
- **Treat an embedding model change as a re-embed.** The same model at different quantizations produces different vectors, so embedding the corpus with one and querying with another silently degrades retrieval — nothing errors, results just get worse. Running the same in-process model on both sides avoids this entirely, which is the main reason it is not configurable per environment.

### Deployment note for the embedding model

`fastembed` downloads the model to a cache directory on first use, defaulting to a temporary directory. That is fine locally but wrong in a container, which would re-download on every cold start and take a network dependency at startup. Phase 10 should bake the model into the image at build time and set `EMBEDDING_CACHE_DIR` to that path.

## 3. Traps in the existing code

Each turns an obvious implementation into a wrong one. Verified by inspection.

1. **`raw_document_path` is not a portable storage key.** `LocalDataStorage.save_text` returns an absolute path (`storage.py:84`); `AzureBlobDataStorage` returns the bare blob name (`storage.py:148`). Reading it back through `read_text()` works in one environment and breaks in the other. Re-derive with `filing_blob_name(company.ticker, document.year, document.quarter)`, deterministic because `FilingImportService` passes the same triple to both `fetch_filing` and the `Document`.
2. **`Company.CIK` is a quoted, case-sensitive Postgres column** (`"CIK" VARCHAR(255)`). NL2SQL emitting `SELECT cik FROM companies` fails. The schema prompt must show it quoted, and a test must assert the quoting survives prompt edits.
3. **`financial_metrics.period` is `"Q1"` but `documents.quarter` is `2`.** Without an explicit instruction the model emits `WHERE period = 2`. The schema prompt must say to filter on `documents.quarter` and join.
4. **The autouse `stub_db_session` fixture in `tests/conftest.py` replaces `get_session` with `MagicMock(spec=Session)`.** A MagicMock returns Mock objects from `session.execute(...)`, so an agent route test would pass while asserting nothing. Agent route tests must override it with a real SQLite session.
5. **The dispatch loop needs its own hard step bound.** Two latches govern the graph — `acquired` per subquery and a global `acquisitions` budget — but a routing bug can still cycle between nodes without advancing either. Cap total node visits, derived from the configured bounds, and raise rather than spin.
6. **`alembic revision --autogenerate` produces a broken migration for `Vector` columns** — it emits the type without the import, never emits `CREATE EXTENSION`, and on later autogenerates tries to drop the HNSW index it cannot model. Write vector migrations by hand and add an `include_object` hook to `migrations/env.py`.
7. **`ingestion/filings_storage.py` is dead duplicate code** — a second `filing_blob_name`, a second protocol, a second Azure class, imported by nothing. Delete it before adding a read path, or someone adds it to the wrong file.
8. **`get_engine()` is `lru_cache`d**, so a read-only engine cannot be built by re-calling it with different `connect_args`. Use `get_engine().execution_options(postgresql_readonly=True)`, which returns an `OptionEngine` sharing the parent's pool — zero extra connections, characteristic reset on return to the pool, and dialect-namespaced so it is silently ignored on SQLite and tests keep working.

## 4. Phases

Each phase leaves the repo green under `uv run ruff check . && uv run ruff format --check . && uv run pyrefly check && uv run pytest`, and each is independently mergeable.

| # | Phase | Status | Adds dependencies |
| --- | --- | --- | --- |
| 1 | Storage read path | in progress | no |
| 2 | Chunk schema and migration | in progress | no |
| 3 | Table-aware markdown chunking | in progress | `langchain-text-splitters` |
| 4 | Chunk import service and route | in progress | `fastembed` |
| 5 | Read-only SQL execution | not started | no |
| 6 | Agent scaffolding | not started | no |
| 7 | Nodes and prompts | not started | no |
| 8 | Graph and API | not started | no |
| 9 | Evaluation harness | not started | no |
| 10 | Deployed inference and front end | not started | one chat provider SDK |
| 11 | Documentation | not started | no |

Phases 1–4 are the current slice and are specified in the approved plan. Phases 5–11 follow.

### Phase 5 — Read-only SQL execution

`get_readonly_engine()` / `get_readonly_session_factory()` in `db/database.py`, per trap 8.

`services/sql_query.py` with a pure `guard_select_sql`. **Ordering matters:** strip comments and empty string literals *before* scanning keywords, so `WHERE name = 'Update Inc'` is not a false positive and `WHERE x = 'a; DROP TABLE y'` is not a false negative; match whole words, which is what catches `WITH t AS (DELETE FROM companies RETURNING *) SELECT * FROM t` — a CTE-wrapped write that a plain `startswith("select")` check waves straight through; return the *original* SQL so literals survive to execution. Execute with `SET LOCAL statement_timeout`, `fetchmany(row_limit + 1)` to detect truncation without materializing everything, and `finally: session.rollback()` so the pooled connection goes back clean.

The regex guard is defence in depth and good error messages. **The `READ ONLY` transaction is the actual enforcement.** The real hardening is a least-privilege Postgres role with `GRANT SELECT` on three tables; document that in `docs/agent.md` as the production recommendation rather than adding a config fallback.

Verify both layers independently: the guard rejects an `INSERT`, and bypassing the guard still fails on the read-only transaction.

### Phase 6 — Agent scaffolding, no graph

`agent/{constants,errors,schema,state,parsing,rerank,routing}.py` and `services/chunk_retrieval.py`. Every file is a pure function or a thin protocol, testable with no graph and no I/O.

`agent/state.py` holds a frozen `AgentState` dataclass and an `AgentStateUpdate` of optional fields, so every node has a real return type rather than `dict[str, Any]`. `current` is a frozen `SubqueryRecord` mutated by `dataclasses.replace`. The dispatch loop merges each node's update into the state, appending to the accumulators (`history`, `citations`, `errors`) and adding to the counters (`iteration`, `acquisitions`), so nodes return **deltas** and never rebuild a list.

Termination has two independent latches: `acquired` on the subquery record stops `subquery → acquire → retrieve → sql → acquire` ping-ponging, and a global `acquisitions` budget caps total SEC round-trips per request. Both live in graph state, not module constants, so routers stay pure and tests can set `max_iterations=2` without monkeypatching.

`agent/schema.py` generates the schema prompt from `METRIC_FIELDS` so it cannot drift from the model, and encodes traps 2 and 3.

`agent/rerank.py` holds BM25 and reciprocal rank fusion in about thirty lines of stdlib. Do not add `rank-bm25`: it imports numpy at module scope, and numpy is not a declared dependency of this project.

Also add `search_similar` to `DocumentChunkRepository`, split into a pure `build_search_statement(...)` and a thin executor. It must compile to the `<=>` **operator** — `func.cosine_distance(...)` does not use the HNSW index and silently turns every query into a sequential scan. Test the compiled SQL, since SQLite cannot run `<=>`.

### Phase 7 — Nodes and prompts

`agent/prompts/` transcribing the paper's Appendix G templates. The decomposition prompt loses `{table_content}` and gains the subquery-answer history plus the fixed schema; the intermediate-answer prompt keeps its cross-validation instructions close to verbatim — prefer SQL on conflict, fall back to text when SQL errored, explain discrepancies.

`agent/nodes/*.py`, one callable class per node, constructor-injected. Each is testable on its own against a hand-built `AgentState`, before any graph exists.

The decompose contract is one of two JSON shapes:

```json
{"action": "subquery", "subquery": "...", "tickers": ["AAPL"], "years": [2024], "quarters": [3]}
{"action": "answer"}
```

This is what makes the paper's `solve_subquery` tool work without requiring native tool calling, and it hands `retrieve` its filters and `acquire` its target for free.

### Phase 8 — Graph and API

`agent/graph.py` — `build_agent_graph(session, text_generator, embedder, ...)` returns the node table mapping each node name to its callable, with both backends injected and never constructed here; that injection is what lets the eval harness swap them. Built per request, which keeps the session lifetime scoped to the request, matching `Depends(get_session)`.

`agent/runner.py` holds the dispatch loop: start at `decompose`, call the current node, merge its update, ask the router for the next node, stop at `finalize`. It enforces the hard step bound from trap 5.

Route `POST /api/v1/agent/query`, sync `def` like every existing route — the persistence stack is sync SQLAlchemy and the dispatch loop is sync, and FastAPI already runs sync routes in a threadpool. The response exposes a per-subquery `steps` trace: it is what turns "the answer is wrong" into "iteration 2's NL2SQL forgot to quote `CIK`", what the eval harness scores component-wise, and what the front end renders.

Document the concurrency ceiling: a 30–120s run occupies one of anyio's 40 threadpool workers against `max_replicas = 1`, so the answer to throughput later is `202 Accepted` plus a job table, not async/await.

The graph test asserts the **visit sequence**, not just the final answer — a final-answer assertion alone passes even if `route_sql` never fired. A second test covers the acquisition path and asserts `acquire` is visited exactly once.

### Phase 9 — Evaluation harness

Code in `src/financial_data_agent/evaluation/` so ruff, pyrefly and the import path treat it like the rest of the package; data and results in `evals/` at the repo root. Add `evals` to `.dockerignore`.

- `dataset.py` — JSONL records `{id, question, answer, answer_type, source, scope, gold_sql, hops, tags}`, where `source ∈ {sql, text, both}` mirrors the paper's single-source/multi-source split.
- `generate.py` — builds the metric half **deterministically** from `financial_metrics` rows via templates, gold answers read straight from the database. This is where the project is better off than the paper, which needed two human annotators per answer. The narrative half is LLM-drafted from chunks for manual review.
- `metrics.py` — `numeric_match` with tolerance and `exact_match` (no judge, free, reproducible), `sql_execution_match` comparing result sets against `gold_sql`, `retrieval_hit_rate`, plus `iterations`, `terminated_at_max` (the paper's "refusal or exceeding max iteration" bucket) and per-step latency.
- `judge.py` — the paper's binary 0/1 evaluation prompt (Appendix G), narrative answers only, judge model and provider pinned independently of the model under test.
- `run.py` — `--provider` and `--model` are first-class axes, so *which backend to adopt* is an output of the harness rather than an input to the design. `--no-decomposition`, `--no-sql`, `--no-retrieval` reproduce the paper's Figure 4 ablations; `--reranker bm25|llm|none` settles the reranking question on evidence.
- `compare.py` — a markdown table across runs, refusing to compare runs whose judge model, embedding model or dataset hash differ.

### Phase 10 — Deployed inference and the front end

Wire the hosted provider into the deployed path: its API key as a Terraform secret alongside `database-url` in `iac/environments/{test,prod}/main.tf`, following the existing `secrets` / `secret_env_vars` pattern, plus the provider and model names as plain `env_vars`. The container-app module needs no changes — it already iterates secret names generically.

The front end is **GitHub Pages**: a static page calling `POST /api/v1/agent/query` from the visitor's browser and rendering the answer plus the `steps` trace. Source in a `demo/` directory, published by a new job in the existing workflow. **Do not use the "deploy from `/docs`" Pages option** — `docs/` holds the design documents and Pages would publish those. Add `demo` to `.dockerignore`.

This means the app needs CORS, which it has never had: `CORSMiddleware` in `api/main.py` allowing the Pages origin specifically, never `*`, with the origin read from config so local development can allow `localhost`.

Confirm before closing the phase: the Container App scales to zero, so the first request after idle pays a *container* cold start even though the inference API does not — decide whether that is acceptable or whether `min_replicas` should be 1. The demo endpoint is public, so decide on a rate limit. And `/docs` is public too, which is fine but worth a deliberate look before the link goes on a CV.

### Phase 11 — Documentation

- `docs/architecture.md` rewritten. Mermaid, not draw.io: it is the established convention, renders on GitHub and diffs as text. Consecutive section numbering — the current file skips 1→3 and ends on an empty `### FastAPI backend` stub. Two diagrams mirroring the paper's Figure 2 split, offline construction and the online loop, reusing the existing node-naming and banner-comment conventions.
- `docs/agent.md` — why schema retrieval was dropped, how `route_sql` replaces the table-chunk trigger, the acquisition policy and its two latches, HNSW versus IVFFlat, the read-only SQL threat model and the least-privilege-role recommendation, the two Protocols and how to add a chat adapter, why the orchestration is hand-rolled rather than LangGraph, why embeddings run in process while the chat model is hosted, and the MCP decision with the alternative stated and rejected.
- `docs/evaluation.md` — dataset format, metric definitions, how to add a model or provider, and what invalidates a cross-run comparison.
- `docs/infrastructure.md` — the inference API key joining `database-url` in the secret-provenance table, the Pages front end as a component Terraform does not own, and the Pages deploy job in the pipeline walkthrough. While here, fix the stale line at `infrastructure.md:85` claiming `az acr build` builds the image; the workflow uses `docker/build-push-action` with buildx.
- `README.md`, `agent/README.md`, `evals/README.md` — commands only, under 50 lines, each ending in a `## Further reading` link.
- `AGENTS.md` — the folder tree, the `api → agent → services` layering line, and one new rule: read-model dataclasses returned by repositories may be imported by the layers above.

## 5. Dependency rules

Pin exactly rather than by range: this is a benchmarking harness, and a silent minor bump that changes prompt formatting or structured-output behaviour invalidates recorded numbers.

Chunking uses `langchain-text-splitters`; nothing else in the project depends on a LangChain package, and the orchestration deliberately does not. Embeddings are `fastembed` on onnxruntime; a chat backend will be a provider SDK behind the `TextGenerator` Protocol, imported inside the branch that builds it.

Do not add:

- `langchain`, `langchain-community`, `langgraph` — a framework dependency tree for what is a Protocol and a dispatch loop here. `langchain-text-splitters` is the exception and is a core dependency; it brings `langchain-core` and `langsmith` with it.
- `sentence-transformers`, `transformers`, `FlagEmbedding` — each drags in roughly 2.5GB of torch, past the 1Gi container limit. This is why the fallback reranker is BM25.
- `tiktoken` — downloads encoding files from a CDN on first use, a runtime network call in a container with no egress guarantee. `len(text) // 4` is sufficient for chunk sizing.
- `rank-bm25` — imports numpy at module scope, and numpy is not a declared dependency of this project.

When a chat provider SDK is added, check what telemetry it ships with and disable it explicitly in the Dockerfile `ENV` block. Filing text should not leave the container by default.

## 6. Testing notes

Follow the three patterns already in `tests/`: monkeypatch the imported name in the *service* module; a real in-memory SQLite session plus `app.dependency_overrides` for repository round-trips; hand-written fakes for external I/O.

`uv run pytest` must pass **with no provider extra installed** — that is what proves the seam holds.

A `FakeChatModel` with scripted responses and a `FakeEmbedder` returning deterministic vectors keep graph tests free of network and of any provider. Derive the fake's vector index with `zlib.crc32`, **not** `hash()`: Python's string hash is salted per process, giving a test that passes locally and fails one CI run in three.

## 7. Chunking

`MarkdownHeaderTextSplitter` cuts sections on headings, `RecursiveCharacterTextSplitter` splits the prose inside them, and table blocks are routed around the recursive splitter entirely.

That last part is not optional. `RecursiveCharacterTextSplitter` separates on `["

", "
", " ", ""]`, so a table longer than `chunk_size` is cut between rows: measured on a 60-row table at `chunk_size=400`, it produced five pieces of which one retained the header row. The other four are columns of numbers with nothing naming them. This is the failure the paper opens with, and `is_table` is what `route_sql` keys on in Phase 6, so a chunk that is half a table is wrong twice over.

`char_start` / `char_end` were dropped when chunking moved to these splitters. `MarkdownHeaderTextSplitter` rejoins lines with `"  
"` and both splitters strip, so chunk content is not a verbatim substring of the source and the offsets could not be recovered honestly. Citations use `accession_number`, `chunk_index` and `heading_path` instead.

Token counts remain a `len(text) // 4` heuristic, and `RecursiveCharacterTextSplitter` is given `max_tokens * 4` characters. Both are approximate, and dense numeric tables tokenize worse than the heuristic suggests.
