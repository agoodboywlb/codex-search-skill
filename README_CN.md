# Codex Search

[English](README.md)

面向 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 的网络搜索 Skill，基于 [Codex CLI](https://github.com/openai/codex) 驱动。

Claude Code 本身没有联网搜索能力。本 Skill 通过调用 Codex CLI 进行网页浏览、链接跟踪和多源交叉验证，最终生成结构化的 Markdown 搜索报告。

## 安装

```bash
# 直接 clone 到你项目的 skills/ 目录
cd your-project/skills
git clone https://github.com/agoodboywlb/codex-search-skill.git
# codex-search/ 即为可用的 skill 目录
```

或手动复制：

```bash
cp -r codex-search/ /path/to/your-project/skills/
```

## 前置依赖

- `python3`（3.8+）
- [Codex CLI](https://github.com/openai/codex) 在 `PATH` 中，或通过 `--codex-bin` / `CODEX_BIN` 指定

## 快速开始

```bash
# 同步模式 — 等待结果返回
bash skills/codex-search/scripts/search.sh \
  --prompt "你的搜索问题" \
  --task-name "my-task" \
  --timeout 120

# 后台派发模式 — 立即返回
bash skills/codex-search/scripts/search.sh \
  --prompt "详细行业分析" \
  --task-name "industry-analysis" \
  --dispatch
```

结果默认写入 `codex-search/data/codex-search-results/`。

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--prompt` | 是 | — | 搜索查询内容 |
| `--task-name` | 否 | `search-<时间戳>` | 任务标识符 |
| `--output` | 否 | `data/codex-search-results/<task>.md` | 输出文件路径 |
| `--result-dir` | 否 | `data/codex-search-results` | 结果目录 |
| `--model` | 否 | `gpt-5.2` | 模型名称 |
| `--timeout` | 否 | `120` | 超时秒数 |
| `--codex-bin` | 否 | `PATH` 中的 `codex` | Codex 可执行文件 |
| `--dispatch` | 否 | `false` | 后台运行 |
| `--post-run-hook` | 否 | — | 完成后执行的 shell 命令 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `CODEX_BIN` | 覆盖默认的 `codex` 查找路径 |
| `CODEX_DEEP_SEARCH_RESULT_DIR` | 外部调用时指定默认结果目录 |

## 结果文件

每个任务产出：

| 文件 | 内容 |
|------|------|
| `<task>.md` | 搜索报告（Markdown） |
| `<task>.meta.json` | 任务元数据 + 最终状态 |
| `<task>.raw.log` | Codex 原始输出 |
| `latest-meta.json` | 最近一次任务的快照 |

## Post-Run Hook

```bash
bash skills/codex-search/scripts/search.sh \
  --prompt "GPU 季度市场份额趋势" \
  --task-name "gpu-market" \
  --post-run-hook "./on-search-done.sh"
```

Hook 接收环境变量：`TASK_NAME`、`OUTPUT`、`META_FILE`、`STATUS`、`EXIT_CODE`、`DURATION`。

## 设计特点

- **跨平台** — Python 驱动，macOS / Linux 均可运行
- **无硬编码路径** — 所有路径从 skill 位置或 CLI 参数动态解析
- **任务隔离** — 并发任务互不覆盖
- **超时保护** — 自动终止长时间运行的搜索

## 项目结构

```
codex-search-skill/           <- 仓库根目录
├── README.md                 <- English
├── README_CN.md              <- 中文
└── codex-search/             <- 拷贝此目录到你的 skills/ 下即可
    ├── SKILL.md
    ├── scripts/
    │   ├── search.sh
    │   └── search.py
    └── tests/
        └── test_search.py
```

## 许可证

MIT
