# Codex Deep Search

Deep web search skill powered by [Codex CLI](https://github.com/openai/codex). Designed for complex queries that need multi-source synthesis — when simple search API snippets aren't enough.

## When to Use

- Complex or niche topics needing cross-referencing from multiple sources
- In-depth research, comprehensive analysis
- Brave / other search API results are too shallow

## Requirements

- `python3` (3.8+)
- [Codex CLI](https://github.com/openai/codex) on `PATH`, or set via `--codex-bin` / `CODEX_BIN`

## Quick Start

```bash
# Synchronous — wait for result
bash scripts/search.sh \
  --prompt "Your research query" \
  --task-name "my-task" \
  --timeout 120

# Background dispatch — returns immediately
bash scripts/search.sh \
  --prompt "Detailed industry analysis" \
  --task-name "industry-analysis" \
  --dispatch
```

Results are written to `data/codex-search-results/` by default.

## Parameters

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--prompt` | Yes | — | Research query |
| `--task-name` | No | `search-<timestamp>` | Task identifier |
| `--output` | No | `data/codex-search-results/<task>.md` | Output file path |
| `--result-dir` | No | `data/codex-search-results` | Directory for result artifacts |
| `--model` | No | `gpt-5.2` | Model override |
| `--timeout` | No | `120` | Seconds before auto-stop |
| `--codex-bin` | No | `codex` from `PATH` | Codex executable |
| `--dispatch` | No | `false` | Run search in background |
| `--post-run-hook` | No | — | Shell command executed after completion |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CODEX_BIN` | Override the default `codex` executable lookup |
| `CODEX_DEEP_SEARCH_RESULT_DIR` | Default result directory when wrapped externally |

## Result Files

Each task produces:

| File | Content |
|------|---------|
| `<task>.md` | Search report (Markdown) |
| `<task>.meta.json` | Task metadata + final status |
| `<task>.raw.log` | Raw Codex output |
| `latest-meta.json` | Snapshot of the most recent task |

## Post-Run Hook

```bash
bash scripts/search.sh \
  --prompt "Quarterly GPU market share" \
  --task-name "gpu-market" \
  --post-run-hook "./on-search-done.sh"
```

Hook receives env vars: `TASK_NAME`, `OUTPUT`, `META_FILE`, `STATUS`, `EXIT_CODE`, `DURATION`.

## Design

- **Cross-platform** — Python runner, works on macOS and Linux
- **No hardcoded paths** — all paths resolve from skill location or CLI flags
- **Per-task isolation** — concurrent tasks don't overwrite each other
- **Timeout protection** — auto-stops runaway searches

## Project Structure

```
codex-deep-search/
├── scripts/
│   ├── search.sh      # Entry point (shell wrapper)
│   └── search.py      # Core search runner
├── tests/
│   └── test_search.py
├── SKILL.md            # Skill metadata (for agent frameworks)
└── README.md
```

## License

MIT
