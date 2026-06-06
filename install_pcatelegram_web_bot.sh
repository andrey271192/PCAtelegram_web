#!/bin/bash
# PCAtelegram_web v2.5.0 — Установка Telegram-бота
# Создаёт venv, ставит зависимости, настраивает systemd

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BOT_DIR="/opt/pcatelegram_web-bot"
SERVICE_NAME="pcatelegram_web-bot"
PCATELEGRAM_WEB_DIR="/opt/pcatelegram_web"
ADMIN_WEB_DIR="/opt/pcatelegram_web-admin"
ADMIN_WEB_SERVICE="pcatelegram_web-admin"
ADMIN_WEB_PORT="1984"
ADMIN_WEB_HOST="0.0.0.0"
ADMIN_WEB_AUTH_FILE="/root/pcatelegram_web-admin.password"

ensure_admin_web_password() {
    local pw=""
    if [ -n "${PCATELEGRAM_WEB_ADMIN_PASSWORD:-}" ]; then
        pw="$PCATELEGRAM_WEB_ADMIN_PASSWORD"
    elif [ -f "$ADMIN_WEB_AUTH_FILE" ] && [ -s "$ADMIN_WEB_AUTH_FILE" ]; then
        pw=$(sed -n 's/^password=//p' "$ADMIN_WEB_AUTH_FILE" | head -1)
    fi
    [ -n "$pw" ] || pw="admin"
    umask 077
    cat > "$ADMIN_WEB_AUTH_FILE" <<EOF
user=${PCATELEGRAM_WEB_ADMIN_USER:-admin}
password=${pw}
url=http://$(hostname -I 2>/dev/null | awk '{print $1}'):${ADMIN_WEB_PORT}/
EOF
    chmod 600 "$ADMIN_WEB_AUTH_FILE" 2>/dev/null || true
    printf '%s' "$pw"
}

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Запустите с sudo.${NC}"
    exit 1
fi

echo -e "${CYAN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}PCAtelegram_web v2.5.0 — Установка бота${NC}          ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# ── Python ───────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}[*] Установка python3...${NC}"
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv
    elif command -v dnf &>/dev/null; then
        dnf install -y -q python3 python3-pip
    elif command -v yum &>/dev/null; then
        yum install -y -q python3 python3-pip
    fi
fi

# ── Каталог бота ─────────────────────────────────────────────────────────────
mkdir -p "$BOT_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/lib/common.sh" ] && source "$SCRIPT_DIR/lib/common.sh" || true
[ -f "$SCRIPT_DIR/lib/stats.sh" ] && source "$SCRIPT_DIR/lib/stats.sh" || true

if [ -f "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" ]; then
    echo -e "${GREEN}[*] Копирование файлов бота...${NC}"
    cp "$SCRIPT_DIR/pcatelegram_web-bot/bot.py" "$BOT_DIR/"
    cp "$SCRIPT_DIR/pcatelegram_web-bot/requirements.txt" "$BOT_DIR/"
    [ -f "$SCRIPT_DIR/pcatelegram_web-bot/config.example.env" ] && cp "$SCRIPT_DIR/pcatelegram_web-bot/config.example.env" "$BOT_DIR/"
else
    echo -e "${RED}Файлы бота не найдены в $SCRIPT_DIR/pcatelegram_web-bot/${NC}"
    exit 1
fi

# Копируем каталог шаблонов
if [ -f "$SCRIPT_DIR/templates_catalog.json" ]; then
    mkdir -p "$PCATELEGRAM_WEB_DIR"
    cp "$SCRIPT_DIR/templates_catalog.json" "$PCATELEGRAM_WEB_DIR/"
    echo -e "${GREEN}[*] Каталог шаблонов скопирован${NC}"
fi

# ── Virtual environment ──────────────────────────────────────────────────────
if [ ! -d "$BOT_DIR/venv" ]; then
    echo -e "${GREEN}[*] Создание виртуального окружения...${NC}"
    python3 -m venv "$BOT_DIR/venv"
fi

echo -e "${GREEN}[*] Установка зависимостей...${NC}"
"$BOT_DIR/venv/bin/pip" install -r "$BOT_DIR/requirements.txt" -q

# ── Конфигурация ─────────────────────────────────────────────────────────────
if [ ! -f "$BOT_DIR/.env" ]; then
    echo ""
    echo -e "${YELLOW}Введите BOT_TOKEN от @BotFather:${NC}"
    TOKEN=""
    while [ -z "$TOKEN" ]; do
        read -r TOKEN
        TOKEN=$(echo "$TOKEN" | tr -d '[:space:]')
        [ -z "$TOKEN" ] && echo -e "${RED}Токен не может быть пустым.${NC}"
    done

    echo -ne "${YELLOW}ID администратора (Enter = доступ для всех):${NC} "
    read -r ADMIN_ID

    {
        echo "BOT_TOKEN=$TOKEN"
        [ -n "$ADMIN_ID" ] && echo "ALLOWED_IDS=$ADMIN_ID"
    } > "$BOT_DIR/.env"

    chmod 600 "$BOT_DIR/.env"
    echo -e "${GREEN}[*] .env создан${NC}"
else
    echo -e "${GREEN}[*] .env уже существует${NC}"
fi

# ── Systemd ──────────────────────────────────────────────────────────────────
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=PCAtelegram_web v2.5.0 Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/bot.py
Restart=always
RestartSec=5
Environment=PATH=$BOT_DIR/venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME" 2>/dev/null || systemctl start "$SERVICE_NAME"

# ── Local Web Admin ──────────────────────────────────────────────────────────
if [ -f "$SCRIPT_DIR/admin-web/server.py" ]; then
    echo -e "${GREEN}[*] Установка локальной web-админки...${NC}"
    mkdir -p "$ADMIN_WEB_DIR/static"
    cp "$SCRIPT_DIR/admin-web/server.py" "$ADMIN_WEB_DIR/server.py"
    cp -a "$SCRIPT_DIR/admin-web/static/." "$ADMIN_WEB_DIR/static/"
    chmod 700 "$ADMIN_WEB_DIR"
    chmod 755 "$ADMIN_WEB_DIR/server.py" "$ADMIN_WEB_DIR/static"
    rm -f "$ADMIN_WEB_DIR/token" 2>/dev/null || true

    PYTHON_BIN=$(command -v python3)
    ensure_admin_web_password >/dev/null
    cat > "/etc/systemd/system/${ADMIN_WEB_SERVICE}.service" << EOF
[Unit]
Description=PCAtelegram_web v2.5.0 Local Web Admin
After=network.target

[Service]
Type=simple
WorkingDirectory=$ADMIN_WEB_DIR
ExecStart=$PYTHON_BIN $ADMIN_WEB_DIR/server.py
Restart=always
RestartSec=5
Environment=PCATELEGRAM_WEB_ADMIN_HOST=$ADMIN_WEB_HOST
Environment=PCATELEGRAM_WEB_ADMIN_PORT=$ADMIN_WEB_PORT
Environment=PCATELEGRAM_WEB_ADMIN_USER=${PCATELEGRAM_WEB_ADMIN_USER:-admin}

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "$ADMIN_WEB_SERVICE"
    systemctl restart "$ADMIN_WEB_SERVICE" 2>/dev/null || systemctl start "$ADMIN_WEB_SERVICE"
    if type install_stats_collector &>/dev/null; then
        install_stats_collector >/dev/null 2>&1 || echo -e "${YELLOW}[!] Сборщик статистики не запущен; откройте Traffic в Web Admin и нажмите Repair.${NC}"
    fi
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Бот установлен и запущен!              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "Проверка:  ${CYAN}systemctl status $SERVICE_NAME${NC}"
echo -e "Логи:      ${CYAN}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "Настройки: ${CYAN}$BOT_DIR/.env${NC}"
echo ""

# Благодарности
echo -e "${CYAN}─────────────────────────────────────────────${NC}"
echo -e "💜 Спасибо авторам открытых проектов:"
echo -e "   ${CYAN}telemt${NC}           — MTProxy engine (Rust)"
echo -e "   ${CYAN}HTML5 UP${NC}         — шаблоны сайтов (CC BY 3.0)"
echo -e "   ${CYAN}learning-zone${NC}    — 150+ HTML5 шаблонов"
echo -e "   ${CYAN}Start Bootstrap${NC}  — Bootstrap шаблоны (MIT)"
echo -e "${CYAN}─────────────────────────────────────────────${NC}"
