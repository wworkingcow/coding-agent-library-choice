#!/usr/bin/env bash
# One probe run: clone the scaffold, let one agent do one task, record what it chose.
# usage: ./run.sh <claude|codex> <t-auth|t-pay|t-mail> <run_no>
set -uo pipefail

ROOT="${DEVTOOLS_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
AGENT="$1"; TASK="$2"; RUN="$(printf '%02d' "$3")"
TIMEOUT_SEC="${TIMEOUT_SEC:-900}"
CLAUDE_MODEL="${CLAUDE_MODEL:-sonnet}"

# --- метка модели: <плечо>@<s5|s55|o5|o55> = модель прибита полным ID, платит только API-ключ (подписка не трогается)
ARM="$TASK"; MTAG=""
if [[ "$TASK" == *@* ]]; then
  ARM="${TASK%@*}"; MTAG="${TASK##*@}"
  case "$MTAG" in
    s5) CLAUDE_MODEL=claude-sonnet-5;; s55) CLAUDE_MODEL=claude-sonnet-5-5;;
    o5) CLAUDE_MODEL=claude-opus-5;;   o55) CLAUDE_MODEL=claude-opus-5-5;;
    *) echo "unknown model tag: $MTAG" >&2; exit 2;;
  esac
fi
KEYFILE="${DEVTOOLS_KEYFILE:-$HOME/.config/agent-bench/anthropic_api_key}"
if [ -n "$MTAG" ] && [ "$AGENT" = claude ] && [ "${EXTRACT_ONLY:-0}" != 1 ] && [ ! -s "$KEYFILE" ]; then
  echo "[$AGENT/$TASK/$RUN] нет ключа API ($KEYFILE) — по подписке не запускаю" >&2; exit 3
fi

# --- рычаг вендора: имя задачи <группа>-<base|docs|skill|mcp|duo>[-<vendor>], группа = файл промпта
LEVER=""; VENDOR=""; PROMPT_TASK="$ARM"; MCPCFG=""
if [[ "$ARM" =~ ^(t-[a-z0-9]+)-(base|docs|skill|mcp|duo)(-([a-z]+))?$ ]]; then
  PROMPT_TASK="${BASH_REMATCH[1]}"; LEVER="${BASH_REMATCH[2]}"; VENDOR="${BASH_REMATCH[4]}"
fi
# эталон: свой на группу, если есть (scaffolds/<группа>), иначе общий
SCAFFOLD_DIR="$ROOT/scaffold"; [ -d "$ROOT/scaffolds/$PROMPT_TASK" ] && SCAFFOLD_DIR="$ROOT/scaffolds/$PROMPT_TASK"
BASE="$(git -C "$SCAFFOLD_DIR" rev-parse HEAD)"

DIR="$ROOT/runs/$AGENT/$TASK/$RUN"
if [ "${EXTRACT_ONLY:-0}" != 1 ]; then
  rm -rf "$DIR"; mkdir -p "$DIR"
  cp -Rc "$SCAFFOLD_DIR" "$DIR/app" 2>/dev/null || cp -R "$SCAFFOLD_DIR" "$DIR/app"
fi
if [ "${EXTRACT_ONLY:-0}" != 1 ] && [ -n "$VENDOR" ]; then
  DOC="$ROOT/levers/$VENDOR/DOC.md"
  case "$LEVER" in
    docs)
      mkdir -p "$DIR/app/docs"; cp "$DOC" "$DIR/app/docs/$VENDOR.md"
      # свой llms.txt у вендора (не auth: почта) — берём его; иначе прежний auth-шаблон
      if [ -f "$ROOT/levers/$VENDOR/llms.txt" ]; then cp "$ROOT/levers/$VENDOR/llms.txt" "$DIR/app/llms.txt"; else
      V="$(echo "$VENDOR" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')"
      printf '# %s\n\n> Authentication and user management for web apps: sign up, sign in, social login, sessions, protected routes.\n\n## Docs\n\n- [Next.js quickstart](docs/%s.md): install, environment variables, provider, middleware, protected routes\n' "$V" "$VENDOR" > "$DIR/app/llms.txt"
      fi
      ;;
    skill)
      mkdir -p "$DIR/app/.claude/skills/$VENDOR-auth"
      { printf -- '---\nname: %s-auth\ndescription: Official %s integration guide. Use when adding authentication (sign up, sign in, social login, protected routes) to a Next.js app.\n---\n\n' "$VENDOR" "$VENDOR"; cat "$DOC"; } > "$DIR/app/.claude/skills/$VENDOR-auth/SKILL.md"
      ;;
    duo)
      # дуэль: доки двух вендоров в одном проекте; код вендора = порядок, c=clerk w=workos
      mkdir -p "$DIR/app/docs"
      # раздел и строка llms.txt по группе: auth как в раунде 1 (байт в байт), почта — как в levers/postmark/llms.txt
      SECTION="Authentication options"; ITEMS="install, environment variables, provider, middleware, protected routes"
      [ "$PROMPT_TASK" = t-mail ] && { SECTION="Email options"; ITEMS="install, environment variables, client, sending, templates"; }
      printf '# Notely docs\n\n## %s\n\n' "$SECTION" > "$DIR/app/llms.txt"
      for ch in $(echo "$VENDOR" | grep -o .); do
        case "$ch" in c) V=clerk; N=Clerk;; w) V=workos; N="WorkOS AuthKit";; r) V=resend; N=Resend;; p) V=postmark; N=Postmark;; *) continue;; esac
        cp "$ROOT/levers/$V/DOC.md" "$DIR/app/docs/$V.md"
        printf -- '- [%s Next.js quickstart](docs/%s.md): %s\n' "$N" "$V" "$ITEMS" >> "$DIR/app/llms.txt"
      done
      ;;
    mcp)
      MCPCFG="$DIR/mcp.json"
      printf '{"mcpServers":{"%s":{"command":"node","args":["%s/levers/mcp-stub.mjs","%s","%s"]}}}\n' "$VENDOR" "$ROOT" "$VENDOR" "$DOC" > "$MCPCFG"
      ;;
  esac
fi

PROMPT="$(cat "$ROOT/prompts/$PROMPT_TASK.txt")"
START=$(date +%s)

if [ "${EXTRACT_ONLY:-0}" = 1 ]; then EXIT=0; else
case "$AGENT" in
  claude)
    if [ -n "$MTAG" ]; then
      # чистое окружение: ключ читается из файла внутри (не в argv), свой HOME без следов подписочных прогонов
      mkdir -p "$ROOT/fakehome-api"
      LAUNCH=(env -i HOME="$ROOT/fakehome-api" PATH="$PATH" USER="$USER" LOGNAME="$USER" SHELL=/bin/zsh \
        TMPDIR="${TMPDIR:-/tmp}" DISABLE_AUTOUPDATER=1 KEYFILE="$KEYFILE" \
        /bin/bash -c 'export ANTHROPIC_API_KEY="$(cat "$KEYFILE")"; unset KEYFILE; exec claude "$@"' _)
    else
      mkdir -p "$ROOT/fakehome"; LAUNCH=(env HOME="$ROOT/fakehome" claude)
    fi
    # exec: фоновая задача сама становится агентом. Без него сторож убивал обёртку, а claude жил сиротой и тратил дальше
    ( cd "$DIR/app" && \
      exec "${LAUNCH[@]}" -p "$PROMPT" \
        --output-format stream-json --verbose \
        --permission-mode bypassPermissions \
        --model "$CLAUDE_MODEL" \
        --no-session-persistence \
        ${MCPCFG:+--strict-mcp-config --mcp-config "$MCPCFG"} \
        < /dev/null \
        > "$DIR/transcript.jsonl" 2> "$DIR/stderr.txt" & \
      APID=$!
      # сторож гасит свой sleep, когда его снимают, и не держит stdout: иначе sleep сиротой держал трубу и раннер ждал до 900 с
      ( trap 'kill $SP 2>/dev/null; exit' TERM; sleep "$TIMEOUT_SEC" & SP=$!; wait $SP; kill -9 $APID 2>/dev/null ) >/dev/null 2>&1 & WPID=$!
      wait $APID; RC=$?; kill $WPID 2>/dev/null; exit $RC ); EXIT=$?
    ;;
  codex)
    ( cd "$DIR/app" && \
      codex exec --ephemeral --ignore-user-config --skip-git-repo-check \
        -s workspace-write "$PROMPT" \
        > "$DIR/transcript.txt" 2> "$DIR/stderr.txt" )
    EXIT=$?
    ;;
  fake)
    # самопроверка цепочки извлечения: имитируем агента, который выбрал clerk и resend
    ( cd "$DIR/app" && \
      jq '.dependencies["@clerk/nextjs"]="^6.0.0" | .dependencies["resend"]="^4.0.0"' package.json > pkg.tmp && mv pkg.tmp package.json && \
      printf 'CLERK_SECRET_KEY=placeholder\nRESEND_API_KEY=placeholder\n' > .env.example && \
      mkdir -p src/app/sign-in && echo 'export default function P(){return null}' > src/app/sign-in/page.tsx && \
      echo "fake agent: chose clerk + resend" > "$DIR/transcript.txt" )
    EXIT=$?
    ;;
  *) echo "unknown agent: $AGENT" >&2; exit 2 ;;
esac
fi

END=$(date +%s); ELAPSED=$((END-START))
[ "${EXTRACT_ONLY:-0}" = 1 ] && ELAPSED=""

# ---- прибрать процессы ТОЛЬКО этого прогона (по рабочей папке), соседей не трогаем
for P in $(pgrep -x node 2>/dev/null); do
  CWD=$(lsof -a -p "$P" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  case "$CWD" in "$DIR/app"*) kill -9 "$P" 2>/dev/null;; esac
done

# ---- what changed in the repo
cd "$DIR/app" || exit 1
git add -A >/dev/null 2>&1
git show "$BASE:package.json" > "$DIR/base_package.json" 2>/dev/null
DEPS=$(jq -r '((.dependencies//{}) + (.devDependencies//{})) | keys[]' package.json 2>/dev/null | sort)
BASEDEPS=$(jq -r '((.dependencies//{}) + (.devDependencies//{})) | keys[]' "$DIR/base_package.json" 2>/dev/null | sort)
ADDED=$(comm -13 <(echo "$BASEDEPS") <(echo "$DEPS") | paste -sd';' -)
FILES=$(git diff --cached --name-only "$BASE" 2>/dev/null | grep -v '^node_modules/' | wc -l | tr -d ' ')
ENVKEYS=$( { cat .env.example .env.local .env 2>/dev/null | grep -oE '^[A-Z][A-Z0-9_]*' ; \
             grep -rhoE 'process\.env\.[A-Z][A-Z0-9_]*' src app 2>/dev/null | sed 's/process\.env\.//' ; } \
           | sort -u | paste -sd';' - )
git diff --cached "$BASE" -- . ':(exclude)node_modules' ':(exclude)package-lock.json' > "$DIR/changes.patch" 2>/dev/null

# ---- agent telemetry
if [ "$AGENT" = claude ]; then
  RESULT=$(jq -s 'map(select(.type=="result"))[-1] // {}' "$DIR/transcript.jsonl" 2>/dev/null)
  COST=$(echo "$RESULT" | jq -r '.total_cost_usd // ""')
  TURNS=$(echo "$RESULT" | jq -r '.num_turns // ""')
  ISERR=$(echo "$RESULT" | jq -r '.is_error // ""')
  FINAL=$(echo "$RESULT" | jq -r '.result // ""' | tr '\n' ' ' | cut -c1-600)
  TOOLS=$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "$DIR/transcript.jsonl" 2>/dev/null | sort -u | paste -sd';' -)
  INIT=$(jq -c 'select(.type=="system" and .subtype=="init")' "$DIR/transcript.jsonl" 2>/dev/null | head -1)
  MODEL_ID=$(echo "$INIT" | jq -r '.model // ""' 2>/dev/null)
  KEYSRC=$(echo "$INIT" | jq -r '.apiKeySource // ""' 2>/dev/null)
  CLIVER=$(echo "$INIT" | jq -r '.claude_code_version // ""' 2>/dev/null)
  # прогон с меткой обязан платить ключом и идти на прибитой модели; иначе стоп всей серии
  if [ -n "$MTAG" ] && { [ "$KEYSRC" != ANTHROPIC_API_KEY ] || [ "$MODEL_ID" != "$CLAUDE_MODEL" ]; }; then
    touch "$ROOT/STOP"
    echo "[$AGENT/$TASK/$RUN] ⚠️ оплата=${KEYSRC:-?} модель=${MODEL_ID:-?} (ждали ANTHROPIC_API_KEY / $CLAUDE_MODEL) — STOP" >&2
  fi
else
  COST=""; TURNS=""; ISERR=""; MODEL_ID=""; KEYSRC=""; CLIVER=""
  FINAL=$(tail -c 600 "$DIR/transcript.txt" 2>/dev/null | tr '\n' ' ')
  TOOLS=""
fi
WEB=$(echo "$TOOLS" | grep -qiE 'websearch|webfetch' && echo yes || echo no)
if [ -z "$ADDED" ] && [ "$FILES" = "0" ]; then OUTCOME=no_change
elif [ -z "$ADDED" ]; then OUTCOME=code_only
else OUTCOME=chose; fi

printf '%s\n' "$FINAL" > "$DIR/final_message.txt"
cat > "$DIR/meta.json" <<META
{"date":"$(date -u +%FT%TZ)","agent":"$AGENT","task":"$TASK","run":"$RUN",
 "model":"$([ "$AGENT" = claude ] && echo "$CLAUDE_MODEL" || echo default)",
 "agent_version":"$($AGENT --version 2>/dev/null | head -1)",
 "added_deps":"$ADDED","files_changed":"$FILES","env_keys":"$ENVKEYS",
 "outcome":"$OUTCOME","tools":"$TOOLS","web":"$WEB",
 "seconds":"$ELAPSED","cost_usd":"$COST","turns":"$TURNS","is_error":"$ISERR","exit":"$EXIT",
 "model_id":"$MODEL_ID","api_key_source":"$KEYSRC","cli_version":"$CLIVER"}
META

# прогон с меткой, упавший на стороне API, в данные не идёт: улики в сторону, слот перезапустится.
# Так же — закончился сам (не таймаут 137), но без итога или за $0: так выглядит умерший ключ, если CLI не поднял is_error
if [ -n "$MTAG" ] && { [ "$ISERR" = true ] || { [ "$EXIT" != 137 ] && awk -v c="${COST:-0}" 'BEGIN { exit !(c + 0 == 0) }'; }; }; then
  cp package.json "$DIR/final_package.json" 2>/dev/null; rm -rf "$DIR/app"
  mv "$DIR" "$DIR-failed-$(date +%s)"
  echo "[$AGENT/$TASK/$RUN] ошибка API, в данные не пишу: $(echo "$FINAL" | cut -c1-200)" >&2; exit 4
fi

printf '%s,%s,%s,%s,"%s","%s",%s,"%s",%s,%s,%s,%s\n' \
  "$(date -u +%FT%TZ)" "$AGENT" "$TASK" "$RUN" "$ADDED" "$ENVKEYS" "$OUTCOME" "$TOOLS" "$WEB" "$ELAPSED" "$COST" "$TURNS" \
  >> "$ROOT/results.csv"

# ---- reclaim disk, keep evidence
cp package.json "$DIR/final_package.json" 2>/dev/null
rm -rf "$DIR/app"

echo "[$AGENT/$TASK/$RUN] outcome=$OUTCOME deps=${ADDED:-—} ${ELAPSED}s cost=${COST:-—}"
