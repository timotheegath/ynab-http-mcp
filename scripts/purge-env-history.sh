#!/usr/bin/env bash
#
# purge-env-history.sh — remove .env.dev and .env.prod from every commit.
#
# Rotate the YNAB API key FIRST: rewriting history does not invalidate a
# key that was already published.
#
# Usage: scripts/purge-env-history.sh [repo-path]

set -euo pipefail

REPO="${1:-$(pwd)}"
FILES=(.env.dev .env.prod)

cd "$REPO"
git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: $REPO" >&2; exit 1; }

BACKUP="$HOME/ynab-http-mcp-history-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP" && chmod 700 "$BACKUP"

echo "==> Backing up history and credentials to $BACKUP"
git bundle create "$BACKUP/history.bundle" --all >/dev/null
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    cp -p "$f" "$BACKUP/$f"
    chmod 600 "$BACKUP/$f"
  fi
done

# Collect the key so it can also be scrubbed from any other file it was
# ever pasted into.
EXPRS="$BACKUP/replace.txt"
: > "$EXPRS"
for f in "${FILES[@]}"; do
  git show "HEAD:$f" 2>/dev/null | sed -n 's/^YNAB_API_KEY=//p' | tr -d '"' \
    | while read -r key; do
        if [ -n "$key" ]; then
          printf 'literal:%s==>***REMOVED***\n' "$key" >> "$EXPRS"
        fi
      done || true
done
chmod 600 "$EXPRS"

# git-filter-repo may not be installed; uvx runs it without installing it.
FILTER_REPO=(git filter-repo)
if ! git filter-repo --version >/dev/null 2>&1; then
  FILTER_REPO=(uvx --from git-filter-repo git-filter-repo)
fi

echo "==> Rewriting history"
"${FILTER_REPO[@]}" --force --invert-paths \
  --path "${FILES[0]}" --path "${FILES[1]}" \
  --replace-text "$EXPRS"

# Bring the credential files back as untracked working copies and keep them
# out of the index for good.
missing=""
for f in "${FILES[@]}"; do
  if [ -f "$BACKUP/$f" ]; then
    cp -p "$BACKUP/$f" "$f"
    chmod 600 "$f"
  fi
  if ! grep -qxF "$f" .gitignore 2>/dev/null; then
    missing="$missing $f"
  fi
done
if [ -n "$missing" ]; then
  {
    printf '\n# YNAB credentials — never commit these\n'
    for f in $missing; do printf '%s\n' "$f"; done
  } >> .gitignore
fi

echo "==> Verifying"
fail=0
if git log --all --oneline -- "${FILES[@]}" | grep -c . >/dev/null; then
  echo "  FAIL: the files are still in history" >&2
  fail=1
else
  echo "  ok: no ${FILES[*]} in any commit"
fi

if [ -s "$EXPRS" ]; then
  key="$(sed -n 's/^literal:\(.*\)==>.*$/\1/p' "$EXPRS" | head -1)"
  # No `grep -q`: it exits on the first match and SIGPIPEs the producer,
  # which with `set -o pipefail` turns a hit into a miss.
  if git rev-list --all --objects | awk '{print $1}' | sort -u \
       | git cat-file --batch 2>/dev/null | grep -F "$key" >/dev/null 2>&1; then
    echo "  FAIL: the key is still reachable in some object" >&2
    fail=1
  else
    echo "  ok: the key is not in any reachable object"
  fi
fi

[ "$fail" -eq 0 ] || { echo "history is NOT clean" >&2; exit 2; }

echo
echo "Done. Now:"
echo "  1. Rotate the YNAB API key in YNAB (do this first!)."
echo "  2. Force-push the rewritten history:"
echo "       git push --force --all origin && git push --force --tags origin"
echo "  3. Re-clone locally; old clones still hold the old history."
echo "  4. Ask GitHub Support to purge the cached blobs if the repo is public."
echo "  5. Commit the .gitignore change."
echo
echo "Backup: $BACKUP"
