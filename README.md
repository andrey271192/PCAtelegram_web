# GoTelegram Pro

Отдельный проект GoTelegram Pro: MTProxy на базе `telemt`, Telegram-бот, локальная web-admin панель, статистика, backup/restore, шаблоны сайта.

## Установка

На сервере под `root`:

```bash
curl -fsSL https://raw.githubusercontent.com/andrey271192/gotelegram/main/bootstrap.sh | bash
```

Если репозиторий private, первый `curl` тоже должен получить GitHub token:

```bash
curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://raw.githubusercontent.com/andrey271192/gotelegram/main/bootstrap.sh | \
  GITHUB_TOKEN="$GITHUB_TOKEN" bash
```

После установки команда доступна как:

```bash
gotelegram
```

## Локальная проверка без GitHub

```bash
rsync -a ./ root@SERVER:/opt/gotelegram/
ssh root@SERVER 'chmod +x /opt/gotelegram/install.sh /opt/gotelegram/install_gotelegram_bot.sh /opt/gotelegram/lib/*.sh && ln -sf /opt/gotelegram/install.sh /usr/local/bin/gotelegram && gotelegram'
```

## Состав

| Путь | Назначение |
| --- | --- |
| `bootstrap.sh` | загружает файлы проекта в `/opt/gotelegram` и запускает меню |
| `install.sh` | основное CLI-меню GoTelegram |
| `install_gotelegram_bot.sh` | отдельная установка Telegram-бота |
| `lib/` | общие функции, telemt, nginx/site, stats, backup, i18n |
| `gotelegram-bot/` | Python Telegram bot |
| `admin-web/` | локальная web-admin панель |
| `templates_catalog.json` | каталог HTML-шаблонов |

## Переменные

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `GOTELEGRAM_BASE` | `https://raw.githubusercontent.com/andrey271192/gotelegram/main` | база загрузки файлов |
| `GOTELEGRAM_INSTALL_DIR` | `/opt/gotelegram` | путь установки |
| `GITHUB_TOKEN` / `GH_TOKEN` | пусто | token для private GitHub raw downloads |

## Проверки

```bash
bash -n bootstrap.sh install.sh install_gotelegram_bot.sh lib/*.sh lib/lang/*.sh
rg -i "old-brand-name" .
```
