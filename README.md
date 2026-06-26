# diri-agent-toolbox

Reusable, typed building blocks for LLM agent tools: **HTTP**, **JSON/data/math**, **sandboxed file I/O**, **calendar** (Google Calendar REST), and a generic **CRM HTTP client**. Extracted from the Deepiri Cyrex tool patterns with Pydantic schemas and safe math evaluation (no `eval`).

This package implements the **Deepiri Agent Tools** slice from the internal **Deepiri Repo Division Doc** (Evan / `diri-agent-toolbox`): HTTP, calendar, CRM, file ops, plus **types/schemas/validation**, with code **regrouped** from what historically lived under `diri-cyrex/app/agents/tools/`. **Cyrex is not modified by this repo**—consumers integrate when ready.

### Traceability (Division Doc § Deepiri Agent Tools)

From **`Deepiri Repo Division Doc.txt`** (lines 42–48, paraphrased): the package targets reusable agent tooling—**HTTP, calendar, CRM, file ops**, plus **types, schemas, and validation**—with the canonical Cyrex quarry at **`diri-cyrex/app/agents/tools/`**, **regrouped** here as an installable library. **Cyrex adoption** (dependency + delegation in Cyrex) is a **separate milestone**; this repo stays the portable **single package** until that work is approved.

## Cyrex → toolbox mapping (future replacement guide)

Use this when refactoring **`diri-cyrex`** (`app/agents/tools/comprehensive_api_tools.py` and related callers) to call this library instead of inlined implementations.

### `ComprehensiveAPITools` (portable subset)

| Cyrex tool name    | Toolbox implementation              | `ToolRunner` name (when configured) | Notes                                                                                                 |
| ------------------ | ----------------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `http_get`         | `AsyncHttpToolbox.get`              | `http_get` (requires `http=`)       | Optional URL prefix / private-IP checks; Cyrex historically used plain `httpx` with no allowlist.     |
| `http_post`        | `AsyncHttpToolbox.post`             | `http_post`                         | JSON body via `json_body=`.                                                                           |
| `http_request`     | `AsyncHttpToolbox.request`          | `http_request`                      | Cyrex mapped `data` to query vs JSON ambiguously; toolbox uses explicit `query_params` / `json_body`. |
| `json_parse`       | `data.json_parse`                   | `json_parse`                        |                                                                                                       |
| `json_format`      | `data.json_format`                  | `json_format`                       |                                                                                                       |
| `data_transform`   | `data.data_transform`               | `data_transform`                    |                                                                                                       |
| `calculate`        | `data.calculate` / `safe_calculate` | `calculate`                         | **Not bitwise-identical to Cyrex** (see below).                                                       |
| `statistics`       | `data.statistics_tool`              | `statistics`                        |                                                                                                       |
| `text_summarize`   | `data.text_summarize`               | `text_summarize`                    | Same simple extractive idea as Cyrex.                                                                 |
| `text_extract`     | `data.text_extract`                 | `text_extract`                      |                                                                                                       |
| `get_current_time` | `data.current_time`                 | `current_time`                      | Cyrex used `timezone` + `format` kwargs; pass `timezone_name=` and `format=` to `data.current_time`.  |

### `utility_tools.py`

| Cyrex registration | Toolbox            | `ToolRunner`  | Notes                                                 |
| ------------------ | ------------------ | ------------- | ----------------------------------------------------- |
| `format_json`      | `data.json_format` | `json_format` | Same role.                                            |
| `parse_json`       | `data.json_parse`  | `json_parse`  |                                                       |
| `calculate`        | `data.calculate`   | `calculate`   | Same **AST/safe** behavior as above—not Cyrex `eval`. |

### Division Doc extras (not all were separate Cyrex tool names)

| Intent (Division Doc) | Toolbox                                                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| File ops              | `SandboxedFileToolbox`; runner: `file_read`, `file_write`, `file_list_dir`, `file_stat` (requires `files=`)                                     |
| Calendar              | `GoogleCalendarClient`, `ListEventsQuery`, `CreateEventRequest`; runner: `calendar_list_events`, `calendar_create_event` (requires `calendar=`) |
| CRM                   | `RestCrmClient`; runner: `crm_request` (requires `crm=`)                                                                                        |

### Stays in Cyrex (do not move into this package for v1)

| Cyrex tool / module                                                            | Reason                                 |
| ------------------------------------------------------------------------------ | -------------------------------------- |
| `db_query`, `db_execute`, `db_get_tables`                                      | Postgres / `get_postgres_manager`      |
| `search_documents`, `call_external_api`                                        | API bridge                             |
| `search_web`                                                                   | Placeholder / external API choice      |
| `api_tools.py`                                                                 | Dynamic bridge tools                   |
| `memory_tools`, `pipeline_tools`, `spreadsheet_tools`, `vendor_fraud_tools`, … | Product-specific or DB/runtime coupled |

### `calculate`: migration from Cyrex

Cyrex used `eval()` with a filtered namespace and a **character allowlist** (including `^` as Python **XOR** on integers). This package uses a **restricted AST** evaluator: allowed operators, `math` functions, and constants (`pi`, `e`, `tau`). Some expressions that passed Cyrex may **fail** here; that is intentional for safety. When integrating, add tests for expressions your agents actually emit and adjust prompts or extend the allowed AST nodes if justified.

## Install

```bash
pip install diri-agent-toolbox
```

With Poetry (recommended for development):

```bash
poetry add diri-agent-toolbox
```

Editable (monorepo sibling):

```bash
pip install -e ../../diri-agent-toolbox
# or with poetry:
poetry add --editable ../../diri-agent-toolbox
```

From Git:

```bash
pip install "git+https://github.com/Team-Deepiri/diri-agent-toolbox.git"
```

### Extras

- `langchain`: `pip install diri-agent-toolbox[langchain]` for optional LangChain `StructuredTool` helpers.
- `redis`: `pip install diri-agent-toolbox[redis]` for Redis-backed caching and streaming.
- `numpy`: `pip install diri-agent-toolbox[numpy]` for confidence scoring with NumPy.
- `torch`: `pip install diri-agent-toolbox[torch]` for GPU/device detection.
- `database`: `pip install diri-agent-toolbox[database]` for async PostgreSQL via asyncpg.
- `all`: `pip install diri-agent-toolbox[all]` installs everything.

## Quick start

```python
import asyncio
from diri_agent_toolbox import AsyncHttpToolbox, ToolRunner
from diri_agent_toolbox.files import SandboxedFileToolbox
from pathlib import Path

async def main():
    http = AsyncHttpToolbox(timeout=30.0, allowed_url_prefixes=["https://api.example.com/"])
    files = SandboxedFileToolbox(root_dir=Path("/tmp/agent_sandbox"))
    runner = ToolRunner(http=http, files=files)

    r = await runner.execute("http_get", url="https://httpbin.org/get")
    print(r.success, r.result)

asyncio.run(main())
```

## Security: HTTP

Agent-facing HTTP is dangerous (SSRF). `AsyncHttpToolbox` supports:

- `allowed_url_prefixes`: only URLs starting with one of these strings are allowed (optional; if empty/`None`, prefix check is skipped).
- `block_private_hosts`: blocks literal private/loopback IPv4/IPv6 addresses (checked with `ipaddress`).
- `resolve_dns`: when `True`, performs DNS resolution and blocks hosts that resolve to private/loopback ranges (opt-in to avoid breaking tests with non-resolving mock domains; default `False`).

Prefer an explicit allowlist in production. See module docstrings for details.

## Modules

| Module                            | Purpose                                                          |
| --------------------------------- | ---------------------------------------------------------------- |
| `diri_agent_toolbox.models`       | `ToolResult`, `ToolDefinition`, JSON Schema helpers              |
| `diri_agent_toolbox.http`         | `AsyncHttpToolbox`, `parse_json_or_text`                         |
| `diri_agent_toolbox.data`         | JSON, safe `calculate`, statistics, text helpers, `current_time` |
| `diri_agent_toolbox.files`        | `SandboxedFileToolbox` (async, under `root_dir`)                 |
| `diri_agent_toolbox.calendar_api` | DTOs, `CalendarClient` protocol, `GoogleCalendarClient`          |
| `diri_agent_toolbox.crm`          | DTOs, `RestCrmClient`                                            |
| `diri_agent_toolbox.runner`       | `ToolRunner` — execute named portable tools                      |
| `diri_agent_toolbox.caching`      | `AdvancedCacheManager`, `EmbeddingCache` (Redis + memory LRU)    |
| `diri_agent_toolbox.confidence`   | `ConfidenceCalculator`, scoring, uncertainty estimation          |
| `diri_agent_toolbox.contracts`    | Model contracts, events (Pydantic), AIModel/Service protocols    |
| `diri_agent_toolbox.database`     | `DatabaseToolbox` — async PostgreSQL with asyncpg                |
| `diri_agent_toolbox.device`       | GPU/device detection (CUDA, MPS, CPU fallback)                   |
| `diri_agent_toolbox.logging`      | `StructuredLogger`, `JsonFormatter`, `ErrorLogger`               |
| `diri_agent_toolbox.monitoring`   | `MetricsCollector` — JSONL metrics + alerts                      |
| `diri_agent_toolbox.processing`   | `AsyncBatchProcessor`, `AsyncItemProcessor` — batched/stream     |
| `diri_agent_toolbox.streaming`    | `StreamingClient` — Redis Streams pub/sub, consumer groups       |

## Development

Install dev dependencies and run the same checks as CI:

```bash
poetry install
poetry run ruff check src tests      # lint (imports, bugs, style rules)
poetry run ruff format --check src tests  # formatting must match ruff format
poetry run mypy src
poetry run pytest
```

Or with pip:

```bash
pip install -e ".[dev]"
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
pytest
```

**Pre-commit** (optional, runs ruff + mypy before each commit):

run via `./scripts/pre-commit-check.sh` to activate pre-commit check

afterward, optionall run `python -m pre_commit run --all-files` to manually check

Auto-fix formatting locally: `python -m ruff format src tests`

## License

Apache-2.0 — see [LICENSE](LICENSE).
