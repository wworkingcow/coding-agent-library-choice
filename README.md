# What makes a coding agent pick a library?

Test bench, raw data and write-up for a small controlled experiment: the same "add auth to this
Next.js app, pick whatever you think is best" task, run many times through Claude Code in headless
mode, changing one thing at a time: vendor docs in the project, a project skill, an MCP server,
web search, the model.

**Write-up: [article/ARTICLE.md](article/ARTICLE.md).** Every number in it is filled in from
`stats.json`, which `report_2610.py` computes from the run data in this repository.

## Layout

| Path | What |
|---|---|
| `prompts/` | Task prompts, verbatim. `t-auth.txt` is the main task. |
| `levers/` | Planted vendor texts (`<vendor>/DOC.md`; `postmark/llms.txt` and `resend/llms.txt` for the email task) and `mcp-stub.mjs`, an MCP server whose only tool returns that text. Keyhold is a made-up vendor; `@keyhold/next` does not exist. |
| `run.sh` | One run: copy the app, plant the lever, run `claude -p`, record the diff, added dependencies and telemetry. |
| `runs/claude/<arm>/<run>/` | Every run: `transcript.jsonl` (stream-JSON), `changes.patch`, `base_package.json`, `final_package.json`, `final_message.txt`, `meta.json`. |
| `results.csv` | One row per run, appended by `run.sh`. |
| `report.py` | Round 1 table: which vendor each run picked. |
| `report_2610.py` | Every number in the article, into `stats.json`. |
| `round_2610.py` | Runner for rounds 2 and 3: API key only, spend cap, canary run first; `--spend` prints cost per arm. |
| `article/` | `ARTICLE.template.md` + `build_article.py` → `ARTICLE.md`. |
| `bundles/` | The app the agent starts from, as git bundles (the exact commits), plus the untracked files the runs also saw (`next-env.d.ts`; `.env.example` in `t-auth2`). |

Arm names are `<task>-<lever>-<vendor>`. `t-auth-docs-workos` is the task in `prompts/t-auth.txt`
with WorkOS's quickstart planted as `docs/workos.md` + `llms.txt`. `base` means nothing planted;
`duo-cw` / `duo-wc` put the Clerk and WorkOS docs side by side, order alternated; `t-auth-web` adds
one sentence asking the agent to search the web; `t-auth2-*` starts from a project that already has
next-auth (`prompts/t-auth2.txt`). A suffix such as `@s55` or `@o55` pins the model by full ID and
runs on an API key. Round 2 and 3 arms: `t-mail-*` is the email task (`prompts/t-mail.txt`) with the
same levers (`docs-postmark`, `docs-resend`, `duo-rp` / `duo-pr` for both quickstarts with the
`llms.txt` order alternated); `t-pay-base@s55`, `t-llm-base@s55`, `t-db-base@s55`,
`t-upload-base@s55` and `t-jobs-base@s55` are the bare defaults for the other tasks in `prompts/`.

Also in `runs/` but not analysed in the article: a first pilot across nine task categories, the
folders without a model suffix (`t-auth`, `t-db`, `t-flags`, `t-jobs`, `t-llm`, `t-mail`, `t-pay`,
`t-upload`, `t-vector`; only the mail result is quoted), run on an earlier version of the bench (the real home directory with
`--safe-mode` instead of a fake home), `t-auth-cf` (two runs with a "deployed to Cloudflare Workers" note) and
`t-auth-web` runs 01–02 (earlier bench flags; `report.py` skips them).

## Reproduce

Needs macOS or Linux, Node 20+, git, `jq`, Python 3.9+ and the Claude Code CLI.

```bash
./setup.sh                        # scaffold/ and scaffolds/t-auth2/ from bundles/, then npm ci
./run.sh claude t-auth-base 9     # one more baseline run -> runs/claude/t-auth-base/09/
python3 report.py                 # round 1 table
python3 report_2610.py            # every number -> stats.json
python3 article/build_article.py  # stats.json -> article/ARTICLE.md
python3 round_2610.py --limit 5   # the round 2/3 queue, API key only, stops at $5 (see PLAN inside)
```

`run.sh` overwrites the run folder it is given and appends to `results.csv`, so use a new run
number. Runs use `--permission-mode bypassPermissions`: the agent gets a shell. Use a machine or VM
where that is fine. Each run is killed after 900 s (`TIMEOUT_SEC`). Before this version the limit
ended the recording but not the agent, so transcripts of runs cut at 900 s run on past it; the
`seconds` column is wall-clock time and can be far above the agent's own `duration_ms`. After
round 2 the timer was also changed to stop itself when a run ends: before, it kept the runner
waiting up to 900 s after each run. That delayed the runner only; runs were not affected.

Isolation: plain arms start `claude` with `HOME=./fakehome`, so your global `CLAUDE.md`, settings,
skills, plugins and MCP servers are not loaded; the login comes from your normal credentials
(macOS Keychain) or `ANTHROPIC_API_KEY`. Account-level claude.ai connectors still appear this way,
as they did in round 1. Arms with a model suffix start from an emptied environment with
`HOME=./fakehome-api` and an API key read from `~/.config/agent-bench/anthropic_api_key`; `run.sh`
stops the series if a transcript shows another billing source or model.

## Edits made before publishing

The transcripts are the original ones, with these replacements made by a script:

- Home paths: `/Users/<name>/Projects/<bench folder>` → `/Users/user/bench`, any other
  `/Users/<name>` → `/Users/user`, including the dash-joined form Claude Code uses for project
  folders.
- Names of the operator's claude.ai account connectors → `Connector1`…`Connector7`.
- `ps` output lines about other processes on the host (desktop apps, system daemons) →
  `[host process line removed]`. Processes of the runs themselves stay; their user column (also in
  `lsof` and `ls -l` output) → `user`.
- Values the sandboxed apps generated for themselves: session and CSRF cookies of the local dev
  servers and magic-link and reset tokens → `[redacted]`; `*_SECRET` keys from `openssl rand` →
  `[generated, redacted]`. Placeholder values the agents wrote into `.env.example` files are left
  as they were.
- Session tokens Claude Code passes to its own child processes (`CLAUDE_CODE_…TOKEN=`, visible
  where an agent listed processes with their environment) → `[redacted]`.
- Anything shaped like an Anthropic API key, placeholders included (the `@` arms ran with a real
  one in the agent's environment) → `sk-ant-[redacted]`.
- In `run.sh`: default paths (repository root = script folder, the key file location) and
  `mkdir -p fakehome`.

In round 3 one batch of runs started from a scaffold that a dry run had dirtied (vendor packages
already in `package.json`); those runs were deleted with their `results.csv` rows before anything
was counted, and the scaffold was restored from git. The remaining runs started clean.

Nothing else was changed. `report_2610.py` produces the same `stats.json` on this copy as on the
original data. Comments and log messages in the scripts are partly in Russian, the author's working
language.
