---
name: codex-deep-search
description: Deep web search using Codex CLI for complex queries that need multi-source synthesis. Use when web_search (Brave) returns insufficient results, when the user asks for in-depth research, comprehensive analysis, or says "deep search", "详细搜索", "帮我查一下", or when a topic needs following multiple links and cross-referencing sources.
---

# Codex Deep Search

Use Codex CLI's web search capability for research tasks needing more depth than Brave API snippets.

This skill is designed to run on `macOS` and `Linux`.

## When to Prefer Over web_search

- Complex/niche topics needing multi-source synthesis
- User explicitly asks for thorough/deep research
- Brave results are too shallow or missing context

## Usage

### Dispatch Mode (recommended for long-running research)

```bash
bash ./skills/codex-deep-search/scripts/search.sh \
  --prompt "Your research query" \
  --task-name "notebooklm-research" \
  --dispatch \
  --timeout 120 > /tmp/codex-search.log 2>&1 &
```

After dispatch: tell the user where the metadata and output files are. Notifications are not built in.

### Synchronous Mode (short queries only)

```bash
bash ./skills/codex-deep-search/scripts/search.sh \
  --prompt "Quick factual query" \
  --output "/tmp/search-result.md" \
  --timeout 60
```

Then read the output file and summarize.

### Optional Post-Run Hook

```bash
bash ./skills/codex-deep-search/scripts/search.sh \
  --prompt "Quarterly GPU market share trends" \
  --task-name "gpu-market-share" \
  --post-run-hook "./scripts/on-search-finished.sh"
```

The hook receives:

- `TASK_NAME`
- `OUTPUT`
- `META_FILE`
- `STATUS`
- `EXIT_CODE`
- `DURATION`

## Parameters

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--prompt` | Yes | — | Research query |
| `--task-name` | No | `search-<timestamp>` | Task identifier |
| `--output` | No | `<skill>/data/codex-search-results/<task>.md` | Output file path |
| `--result-dir` | No | `<skill>/data/codex-search-results` | Directory for result artifacts |
| `--model` | No | `gpt-5.3-codex` | Model override |
| `--timeout` | No | `120` | Seconds before auto-stop |
| `--codex-bin` | No | `codex` from `PATH` or `CODEX_BIN` | Codex executable |
| `--dispatch` | No | `false` | Run search in the background |
| `--post-run-hook` | No | — | Shell command executed after completion |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CODEX_BIN` | Overrides the default `codex` executable lookup |
| `CODEX_DEEP_SEARCH_RESULT_DIR` | Optional default result directory when wrapped externally |

## Result Files

| File | Content |
|------|---------|
| `data/codex-search-results/<task>.md` | Search report |
| `data/codex-search-results/<task>.meta.json` | Task metadata + final status |
| `data/codex-search-results/<task>.raw.log` | Raw runner output |
| `data/codex-search-results/latest-meta.json` | Snapshot of the latest task metadata |

## Key Design

- **Cross-platform runtime** - Python runner avoids GNU-only shell features
- **No hardcoded machine paths** - all paths resolve from the skill location or CLI flags
- **Decoupled notifications** - search owns result generation only; external orchestration owns notifications
- **Per-task metadata** - concurrent tasks do not overwrite each other
- **Timeout protection** - auto-stops runaway searches

## Requirements

- `python3` or `python`
- `codex` CLI available on `PATH`, or set with `--codex-bin` / `CODEX_BIN`

## Notes

- Dispatch mode returns immediately with JSON pointing to `meta_file` and `output`.
- If you need notifications, implement them outside this skill or via `--post-run-hook`.
