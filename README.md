# PCAtelegram_web

Отдельный проект PCAtelegram_web: MTProxy на базе `telemt`, Telegram-бот, локальная web-admin панель, статистика, backup/restore, шаблоны сайта.

## Установка

На сервере под `root`:

```bash
curl -fsSL https://raw.githubusercontent.com/andrey271192/PCAtelegram_web/main/bootstrap.sh | bash
```

Если репозиторий private, первый `curl` тоже должен получить GitHub token:

```bash
curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://raw.githubusercontent.com/andrey271192/PCAtelegram_web/main/bootstrap.sh | \
  GITHUB_TOKEN="$GITHUB_TOKEN" bash
```

После установки команда доступна как:

```bash
pcatelegram_web
```

## Локальная проверка без GitHub

```bash
rsync -a ./ root@SERVER:/opt/pcatelegram_web/
ssh root@SERVER 'chmod +x /opt/pcatelegram_web/install.sh /opt/pcatelegram_web/install_pcatelegram_web_bot.sh /opt/pcatelegram_web/lib/*.sh && ln -sf /opt/pcatelegram_web/install.sh /usr/local/bin/pcatelegram_web && pcatelegram_web'
```

## Состав

| Путь | Назначение |
| --- | --- |
| `bootstrap.sh` | загружает файлы проекта в `/opt/pcatelegram_web` и запускает меню |
| `install.sh` | основное CLI-меню PCAtelegram_web |
| `install_pcatelegram_web_bot.sh` | отдельная установка Telegram-бота |
| `lib/` | общие функции, telemt, nginx/site, stats, backup, i18n |
| `pcatelegram_web-bot/` | Python Telegram bot |
| `admin-web/` | локальная web-admin панель |
| `templates_catalog.json` | каталог HTML-шаблонов |

## Переменные

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `PCATELEGRAM_WEB_BASE` | `https://raw.githubusercontent.com/andrey271192/PCAtelegram_web/main` | база загрузки файлов |
| `PCATELEGRAM_WEB_INSTALL_DIR` | `/opt/pcatelegram_web` | путь установки |
| `GITHUB_TOKEN` / `GH_TOKEN` | пусто | token для private GitHub raw downloads |
| `PCATELEGRAM_WEB_ADMIN_HOST` | `127.0.0.1` | bind web-admin |
| `PCATELEGRAM_WEB_ADMIN_PORT` | `1984` | port web-admin |
| `PCATELEGRAM_WEB_ADMIN_USER` | `admin` | Basic Auth login |
| `PCATELEGRAM_WEB_ADMIN_PASSWORD` | пусто | Basic Auth password; обязателен при public bind |

## Web-admin

После первого запуска `pcatelegram_web` локальная web-admin панель ставится как `pcatelegram_web-admin.service`.

Безопасный локальный доступ через SSH tunnel:

```bash
ssh -L 1984:127.0.0.1:1984 root@SERVER
open http://127.0.0.1:1984/
```

Для public bind сначала задайте пароль через systemd override или reverse proxy:

```ini
[Service]
Environment=PCATELEGRAM_WEB_ADMIN_HOST=0.0.0.0
Environment=PCATELEGRAM_WEB_ADMIN_PORT=1984
Environment=PCATELEGRAM_WEB_ADMIN_USER=admin
Environment=PCATELEGRAM_WEB_ADMIN_PASSWORD=change-me
```

Без HTTPS public Basic Auth гонит пароль открытым текстом. Для постоянного доступа лучше reverse proxy с TLS.

## Проверки

```bash
bash -n bootstrap.sh install.sh install_pcatelegram_web_bot.sh lib/*.sh lib/lang/*.sh
rg -i "old-brand-name" .
```
