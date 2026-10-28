#!/usr/bin/env bash
# Rebuilds the two starting projects from bundles/ (the exact commits run.sh diffs against) and installs dependencies.
set -euo pipefail
cd "$(dirname "$0")"

build() {  # <bundle name> <target dir>
  if [ -d "$2/.git" ]; then
    echo "$2: already there, not re-cloning"
  else
    git clone -q "bundles/$1.bundle" "$2"
    git -C "$2" remote remove origin   # the original repos had no remote
  fi
  cp -R "bundles/extra/$1/." "$2/"     # untracked files the runs also saw
  (cd "$2" && npm ci --no-audit --no-fund)
  echo "$2: $(git -C "$2" log --oneline | head -1)"
}

build scaffold scaffold
mkdir -p scaffolds
build t-auth2 scaffolds/t-auth2
