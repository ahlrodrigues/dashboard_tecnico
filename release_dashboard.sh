#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="./.venv/bin/python"

usage() {
  cat <<'EOF'
Uso:
  ./release_dashboard.sh patch
  ./release_dashboard.sh minor --push
  ./release_dashboard.sh major --message "Sua mensagem"
  ./release_dashboard.sh patch --push --message "Sua mensagem"

Opcoes:
  patch|minor|major   Tipo de incremento semantico
  --push              Envia o commit para o remoto apos concluir
  --message TEXTO     Sobrescreve a mensagem gerada automaticamente
EOF
}

require_clean_index() {
  if ! git diff --quiet --cached; then
    echo "Ha alteracoes ja staged. Conclua ou limpe o staging antes de usar o release_dashboard.sh."
    exit 1
  fi
}

collect_changed_files() {
  git status --short --untracked-files=all | awk '{print $2}'
}

join_with_and() {
  local items=("$@")
  local count="${#items[@]}"
  if (( count == 0 )); then
    printf '%s' ""
    return
  fi
  if (( count == 1 )); then
    printf '%s' "${items[0]}"
    return
  fi
  if (( count == 2 )); then
    printf '%s and %s' "${items[0]}" "${items[1]}"
    return
  fi

  local result=""
  local i
  for (( i=0; i<count; i++ )); do
    if (( i == count - 1 )); then
      result+="and ${items[i]}"
    else
      result+="${items[i]}, "
    fi
  done
  printf '%s' "$result"
}

append_part() {
  local value="$1"
  if [[ -z "$value" ]]; then
    return
  fi
  MESSAGE_PARTS+=("$value")
}

generate_commit_message() {
  local changed_files_text="$1"
  MESSAGE_PARTS=()

  if grep -Eq '(^|/)(dashboard_os_sgp\.html|gerar_dashboard\.py)$' <<<"$changed_files_text"; then
    append_part "dashboard layout"
  fi
  if grep -Eq '(^|/)(main\.py|processar_os\.py|sgp_client\.py|dashboard_server\.py)$' <<<"$changed_files_text"; then
    append_part "data pipeline"
  fi
  if grep -Eq '(^|/)(version\.py|bump_version\.py|release_dashboard\.sh)$' <<<"$changed_files_text"; then
    append_part "release tooling"
  fi
  if grep -Eq '(^|/)(README\.md|config\.example\.json)$' <<<"$changed_files_text"; then
    append_part "project docs"
  fi
  if grep -Eq '(^|/)config\.json$' <<<"$changed_files_text"; then
    append_part "local configuration"
  fi

  local joined
  joined="$(join_with_and "${MESSAGE_PARTS[@]}")"
  if [[ -z "$joined" ]]; then
    echo "Update project files"
    return
  fi

  echo "Update $joined"
}

TYPE="${1:-}"
if [[ -z "$TYPE" ]]; then
  usage
  exit 1
fi
shift

case "$TYPE" in
  patch|minor|major) ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Tipo invalido: $TYPE"
    usage
    exit 1
    ;;
esac

PUSH=false
CUSTOM_MESSAGE=""

while (( "$#" )); do
  case "$1" in
    --push)
      PUSH=true
      shift
      ;;
    --message)
      if (( "$#" < 2 )); then
        echo "A opcao --message exige um texto."
        exit 1
      fi
      CUSTOM_MESSAGE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Opcao invalida: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Nao encontrei o interpretador em $PYTHON_BIN"
  exit 1
fi

require_clean_index

CHANGED_FILES="$(collect_changed_files)"
if [[ -z "$CHANGED_FILES" ]]; then
  echo "Nao ha alteracoes para versionar."
  exit 1
fi

COMMIT_MESSAGE="$CUSTOM_MESSAGE"
if [[ -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="$(generate_commit_message "$CHANGED_FILES")"
fi

NEW_VERSION="$("$PYTHON_BIN" bump_version.py "$TYPE")"
echo "Versao atualizada para $NEW_VERSION"

git add -A
git commit -m "$COMMIT_MESSAGE"

"$PYTHON_BIN" main.py --refresh-target none --rebuild-html

git add dashboard_os_sgp.html version.py
git commit --amend --no-edit

if [[ "$PUSH" == true ]]; then
  git push
fi

echo "Release concluido."
echo "Versao: $NEW_VERSION"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Mensagem: $COMMIT_MESSAGE"
