#!/usr/bin/env bash
# PCAtelegram_web — bootstrap installer from this repository.
set -euo pipefail

PCATELEGRAM_WEB_BASE="${PCATELEGRAM_WEB_BASE:-https://raw.githubusercontent.com/andrey271192/PCAtelegram_web/main}"
INSTALL_DIR="${PCATELEGRAM_WEB_INSTALL_DIR:-/opt/pcatelegram_web}"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ "$(id -u)" -ne 0 ]; then
  echo -e "  ${RED}✗${NC} Запустите от root"
  exit 1
fi

for cmd in curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || {
    apt-get update -qq
    apt-get install -y -qq "$cmd" >/dev/null 2>&1
  }
done

FILES=(
  "install.sh" "install_pcatelegram_web_bot.sh" "templates_catalog.json"
  "lib/common.sh" "lib/telemt.sh" "lib/telemt_config.sh" "lib/backup.sh"
  "lib/website.sh" "lib/templates_catalog.sh" "lib/stats.sh" "lib/i18n.sh"
  "lib/lang/en.sh" "lib/lang/ru.sh"
  "pcatelegram_web-bot/bot.py" "pcatelegram_web-bot/i18n.py"
  "pcatelegram_web-bot/lang/en.json" "pcatelegram_web-bot/lang/ru.json"
  "pcatelegram_web-bot/config.example.env" "pcatelegram_web-bot/requirements.txt" "pcatelegram_web-bot/README.md"
  "admin-web/server.py" "admin-web/static/index.html" "admin-web/static/styles.css" "admin-web/static/app.js"
)

curl_headers=()
if [ -n "${GITHUB_TOKEN:-${GH_TOKEN:-}}" ]; then
  curl_headers=(-H "Authorization: Bearer ${GITHUB_TOKEN:-${GH_TOKEN:-}}")
fi

download_file() {
  local remote_path="$1"
  local local_path="$2"
  local attempt http_code

  mkdir -p "$(dirname "$local_path")"
  for attempt in 1 2 3; do
    http_code=$(curl -sL "${curl_headers[@]}" -w "%{http_code}" -o "$local_path" "${PCATELEGRAM_WEB_BASE%/}/${remote_path}" 2>/dev/null || echo "000")
    if [ "$http_code" = "200" ]; then
      return 0
    fi
    sleep 1
  done

  echo -e "  ${RED}✗${NC} Ошибка загрузки ${remote_path} (HTTP ${http_code})"
  return 1
}

echo -e "  ${CYAN}↻${NC} Загрузка PCAtelegram_web из ${PCATELEGRAM_WEB_BASE%/}..."
mkdir -p "${INSTALL_DIR}/lib/lang" "${INSTALL_DIR}/pcatelegram_web-bot/lang" "${INSTALL_DIR}/admin-web/static"

failed=0
for f in "${FILES[@]}"; do
  if download_file "$f" "${INSTALL_DIR}/${f}"; then
    echo -e "  ${GREEN}✓${NC} ${f}"
  else
    failed=$((failed + 1))
  fi
done
[ "$failed" -eq 0 ] || exit 1

chmod +x "${INSTALL_DIR}/install.sh" "${INSTALL_DIR}/install_pcatelegram_web_bot.sh"
chmod +x "${INSTALL_DIR}"/lib/*.sh
chmod +x "${INSTALL_DIR}/admin-web/server.py" 2>/dev/null || true
sed -i 's/\r$//' "${INSTALL_DIR}/install.sh" "${INSTALL_DIR}/install_pcatelegram_web_bot.sh" "${INSTALL_DIR}"/lib/*.sh "${INSTALL_DIR}"/lib/lang/*.sh 2>/dev/null || true
ln -sf "${INSTALL_DIR}/install.sh" /usr/local/bin/pcatelegram_web

exec bash "${INSTALL_DIR}/install.sh" "$@"
