#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

BRANCH="${1:-feature/dashboard-live-api}"
PYTHON_BIN="$BASE_DIR/.venv/bin/python"
LOG_FILE="$BASE_DIR/atualizar_live.log"
ALLOWED_DIRTY_PATHS=(
  "dashboard_os_sgp.html"
  "dashboard_data.json"
)

list_tracked_changes() {
  git status --short --untracked-files=no | awk '{print $2}'
}

path_is_allowed_dirty() {
  local path="$1"
  local allowed
  for allowed in "${ALLOWED_DIRTY_PATHS[@]}"; do
    if [[ "$path" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

cleanup_generated_artifacts() {
  mapfile -t changed_paths < <(list_tracked_changes)
  if (( ${#changed_paths[@]} == 0 )); then
    return
  fi

  local path
  local disallowed=()
  local allowed=()
  for path in "${changed_paths[@]}"; do
    if path_is_allowed_dirty "$path"; then
      allowed+=("$path")
    else
      disallowed+=("$path")
    fi
  done

  if (( ${#disallowed[@]} > 0 )); then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ha alteracoes locais fora dos artefatos gerados permitidos:"
    printf '  - %s\n' "${disallowed[@]}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Limpe ou salve essas alteracoes antes de executar o deploy."
    exit 1
  fi

  if (( ${#allowed[@]} > 0 )); then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Limpando artefatos gerados locais antes do deploy: ${allowed[*]}"
    git restore --worktree --staged --source=HEAD -- "${allowed[@]}"
  fi
}

require_clean_worktree() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ha alteracoes locais no worktree ou no staging. Limpe ou salve antes de executar o deploy."
    exit 1
  fi
}

ensure_remote_branch_exists() {
  if ! git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] A branch origin/$BRANCH nao foi encontrada."
    exit 1
  fi
}

update_branch_safely() {
  local local_sha remote_sha base_sha
  local_sha="$(git rev-parse HEAD)"
  remote_sha="$(git rev-parse "origin/$BRANCH")"
  base_sha="$(git merge-base HEAD "origin/$BRANCH")"

  if [[ "$local_sha" == "$remote_sha" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Branch $BRANCH ja esta atualizada."
    return
  fi

  if [[ "$local_sha" == "$base_sha" ]]; then
    git merge --ff-only "origin/$BRANCH"
    return
  fi

  if [[ "$remote_sha" == "$base_sha" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] A branch local $BRANCH esta a frente do remoto. Envie ou alinhe os commits antes do deploy."
    exit 1
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] A branch local $BRANCH divergiu de origin/$BRANCH. Resolva a divergencia antes do deploy."
  exit 1
}

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando deploy da branch $BRANCH"

  if [[ ! -d "$BASE_DIR/.git" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Este diretório nao e um repositorio git."
    exit 1
  fi

  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ambiente virtual nao encontrado em $PYTHON_BIN"
    exit 1
  fi

  cleanup_generated_artifacts
  require_clean_worktree
  git fetch --prune origin
  ensure_remote_branch_exists
  git checkout "$BRANCH"
  cleanup_generated_artifacts
  require_clean_worktree
  update_branch_safely
  "$PYTHON_BIN" main.py --rebuild-html

  VERSION_LABEL="$("$PYTHON_BIN" -c 'from version import VERSION; print(VERSION)' 2>/dev/null || echo "desconhecida")"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deploy concluido na versao ${VERSION_LABEL} em $(git rev-parse --short HEAD)"
} | tee -a "$LOG_FILE"
