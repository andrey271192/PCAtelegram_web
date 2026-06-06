#!/usr/bin/env python3
"""
PCAtelegram_web v2.5.0 Bot - MTProxy Management for Linux
Manages telemt engine via Telegram interface with full CLI feature parity
Uses python-telegram-bot v21+
Supports EN/RU UI with per-user language preferences.
"""

import asyncio
import csv
import fcntl
import hashlib
import html
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import toml
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from urllib.parse import quote

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.error import TelegramError, BadRequest

# i18n — loaded from the bot directory next to this file
_BOT_DIR = Path(__file__).resolve().parent
if str(_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(_BOT_DIR))
try:
    from i18n import (
        t as _t,
        tf as _tf,
        get_user_lang,
        set_user_lang,
        get_language_name,
        SUPPORTED_LANGS,
    )
except Exception as _i18n_err:  # pragma: no cover — defensive fallback
    logging.warning("i18n module not available: %s", _i18n_err)

    def _t(user_id, key, default=None):
        return default if default is not None else key

    def _tf(user_id, key, *args, default=None):
        template = default if default is not None else key
        try:
            return template % args if args else template
        except Exception:
            return template

    def get_user_lang(user_id):
        return "en"

    def set_user_lang(user_id, code):
        return False

    def get_language_name(code):
        return code

    SUPPORTED_LANGS = ("en",)


def _uid(update: Optional[Update]) -> Optional[int]:
    """Extract user id from an update (if any)."""
    if update is None:
        return None
    user = getattr(update, "effective_user", None)
    return user.id if user else None

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

PCATELEGRAM_WEB_VERSION = "2.5.0"
PCATELEGRAM_WEB_CONFIG = "/opt/pcatelegram_web/config.json"
DISABLED_USERS_FILE = "/opt/pcatelegram_web/disabled_users.json"
USER_STATS_HISTORY = "/opt/pcatelegram_web/user_stats_history.csv"
USER_LOCK_FILE = "/run/pcatelegram_web/admin-users.lock"
TELEMT_CONFIG = "/etc/telemt/config.toml"
TELEMT_SERVICE = "telemt"
WEBSITE_ROOT = "/var/www/pcatelegram_web-site"
BACKUP_DIR = "/opt/pcatelegram_web/backups"
BACKUP_SCHEDULE_FILE = "/opt/pcatelegram_web/backup_schedule.json"
TEMPLATES_CATALOG = "/opt/pcatelegram_web/templates_catalog.json"
INSTALL_SH = "/opt/pcatelegram_web/install.sh"

BOT_TOKEN = os.getenv("BOT_TOKEN")
ENV_FILE = "/opt/pcatelegram_web-bot/.env"
ADMIN_WEB_SERVICE = "pcatelegram_web-admin"
ADMIN_WEB_PORT = 1984


def format_bytes_human(value: int) -> str:
    value = max(0, int(value or 0))
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    if value < 1024 * 1024 * 1024:
        return f"{value / 1024 / 1024:.1f} MB"
    return f"{value / 1024 / 1024 / 1024:.1f} GB"

# ── Загрузка ALLOWED_IDS ────────────────────────────────────────────────────
# Поддерживает запятую, пробел, или их комбинацию как разделитель
ALLOWED_IDS: set = set()
_WAITING_FOR_ADMIN = False  # True если список пуст → ждём первого админа


def _load_allowed_ids() -> None:
    """Загрузить ALLOWED_IDS из переменной окружения."""
    global ALLOWED_IDS, _WAITING_FOR_ADMIN
    raw = os.getenv("ALLOWED_IDS", "")
    ALLOWED_IDS = set()
    # Разделители: запятая, пробел, или оба
    for part in re.split(r'[,\s]+', raw):
        part = part.strip()
        if part:
            try:
                ALLOWED_IDS.add(int(part))
            except ValueError:
                logging.warning(f"Invalid ALLOWED_IDS entry: {part}")
    _WAITING_FOR_ADMIN = len(ALLOWED_IDS) == 0


def _save_allowed_ids() -> None:
    """Сохранить ALLOWED_IDS в .env файл и обновить os.environ."""
    global _WAITING_FOR_ADMIN
    ids_str = ",".join(str(i) for i in sorted(ALLOWED_IDS))
    os.environ["ALLOWED_IDS"] = ids_str
    _WAITING_FOR_ADMIN = len(ALLOWED_IDS) == 0

    if not os.path.exists(ENV_FILE):
        return

    try:
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("ALLOWED_IDS="):
                if ids_str:
                    new_lines.append(f"ALLOWED_IDS={ids_str}\n")
                # Если пусто — удаляем строку
                found = True
            else:
                new_lines.append(line)

        if not found and ids_str:
            new_lines.append(f"ALLOWED_IDS={ids_str}\n")

        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)

        logger.info(f"ALLOWED_IDS updated in .env: {ids_str or '(empty)'}")
    except OSError as e:
        logger.error(f"Failed to update .env: {e}")


_load_allowed_ids()

LITE_DOMAINS = [
    "google.com",
    "microsoft.com",
    "cloudflare.com",
    "apple.com",
    "amazon.com",
    "github.com",
    "stackoverflow.com",
    "medium.com",
    "wikipedia.org",
    "coursera.org",
    "udemy.com",
    "habr.com",
    "stepik.org",
    "duolingo.com",
    "khanacademy.org",
    "bbc.com",
    "reuters.com",
    "nytimes.com",
    "ted.com",
    "zoom.us",
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


async def sh(*args, timeout: int = 60) -> Tuple[int, str, str]:
    """Execute shell command asynchronously.

    Args:
        *args: Command and arguments
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
        return (
            process.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        return (-1, "", f"Command timeout after {timeout}s")
    except Exception as e:
        return (-1, "", str(e))


# Per-host mutex preventing concurrent install.sh --action invocations. Two
# admins hitting "change template" at the same second could race each other
# and corrupt /var/www/pcatelegram_web-site. One global lock is fine — these are
# rare operations and should serialize cleanly.
_BOT_ACTION_LOCK = asyncio.Lock()

# Allowed template-id shape: catalog ids are [a-zA-Z0-9_-], never longer than 64.
# This is a defense-in-depth check before we hand the value to subprocess.
_TPL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Allowed Lite mask domain shape — simple DNS hostname, up to 253 chars total.
# Each label 1–63 chars, labels separated by dots, alphanumerics + hyphens.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+"
    r"(?!-)[A-Za-z0-9-]{2,63}(?<!-)$"
)
_USER_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")
MAX_UNIQUE_IP_LIMIT = 1000000
TELEMT_RESTART_DEBOUNCE_SECONDS = float(os.getenv("PCATELEGRAM_WEB_TELEMT_RESTART_DEBOUNCE", "8"))
_LAST_TELEMT_RESTART = 0.0


class FileLock:
    def __init__(self, path: str):
        self.path = Path(path)
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("w", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


async def run_bot_action(action: str, timeout: int = 300, **params) -> Dict:
    """Invoke install.sh --action=X --json and parse the JSON result.

    Args:
        action: action name (e.g. "change-template", "change-lite-domain")
        timeout: seconds to wait for completion (long ops: template download can take time)
        **params: arbitrary key→value pairs, each passed as --key=value

    Returns:
        dict with at least {"status": "success|error", "message": "..."}.
        Transport errors are mapped to {"status":"error","message":..., "code":"transport"}
    """
    cmd = ["bash", INSTALL_SH, f"--action={action}", "--json"]
    for k, v in params.items():
        if v is None:
            continue
        cmd.append(f"--{k.replace('_', '-')}={v}")

    code, stdout, stderr = await sh(*cmd, timeout=timeout)
    stdout = (stdout or "").strip()

    # install.sh may print multiple log lines to stderr; the JSON is on stdout.
    # Pick the last non-empty line that looks like JSON (robust to any stray output).
    json_line = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            json_line = line
            break

    if json_line:
        try:
            data = json.loads(json_line)
            if isinstance(data, dict) and "status" in data:
                return data
        except json.JSONDecodeError as e:
            logger.warning(f"run_bot_action: JSON parse failed: {e} | line={json_line!r}")

    # No JSON from install.sh — synthesize an error result
    tail = (stderr or "")[-300:] if stderr else ""
    logger.error(
        f"run_bot_action({action}): no JSON output, rc={code}, "
        f"stdout={stdout[-300:]!r}, stderr={tail!r}"
    )
    return {
        "status": "error",
        "message": "install.sh did not return a JSON result",
        "code": "transport",
        "rc": str(code),
    }


def load_json(path: str) -> Optional[Dict]:
    """Load JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def load_toml(path: str) -> Optional[Dict]:
    """Load TOML file."""
    try:
        with open(path, "r") as f:
            return toml.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def save_json(path: str, data: Dict) -> bool:
    """Save JSON file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save {path}: {e}")
        return False


def template_display_name(template_id: str) -> str:
    """Resolve a template id to a human-friendly name from catalog/config."""
    if not template_id:
        return ""
    if template_id in ("deployed_site", "existing_site"):
        return "Existing deployed site"
    if template_id.startswith("custom_"):
        config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
        source = config.get("template_source", "")
        return f"{template_id} ({source})" if source else template_id
    catalog = load_json(TEMPLATES_CATALOG) or {}
    for cat in catalog.get("categories", []):
        for tpl in cat.get("templates", []):
            if tpl.get("id") == template_id:
                return f"{tpl.get('name', template_id)} ({template_id})"
    return template_id


def pro_template_map(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, str]:
    """Return the short callback key -> template id map for this chat."""
    mapping = context.user_data.setdefault("pro_template_map", {})
    if not isinstance(mapping, dict):
        mapping = {}
        context.user_data["pro_template_map"] = mapping
    return mapping


def resolve_pro_template_id(context: ContextTypes.DEFAULT_TYPE, key_or_id: str) -> str:
    """Resolve a short Telegram callback key back to the real template id."""
    mapped = pro_template_map(context).get(key_or_id)
    if mapped:
        return str(mapped)

    catalog = load_json(TEMPLATES_CATALOG) or {}
    for cat in catalog.get("categories", []):
        for tpl in cat.get("templates", []):
            template_id = str(tpl.get("id", ""))
            if hashlib.sha1(template_id.encode("utf-8")).hexdigest()[:12] == key_or_id:
                return template_id

    return str(key_or_id)


def pro_template_key_for_id(context: ContextTypes.DEFAULT_TYPE, template_id: str) -> str:
    """Store a template id behind a short key that fits Telegram callback limits."""
    mapping = pro_template_map(context)
    template_id = str(template_id)
    for key, stored_id in mapping.items():
        if stored_id == template_id:
            return str(key)
    key = hashlib.sha1(template_id.encode("utf-8")).hexdigest()[:12]
    mapping[key] = template_id
    return key


async def safe_edit_message(
    query,
    text: str,
    reply_markup=None,
    parse_mode=None,
    disable_web_page_preview: Optional[bool] = None,
) -> bool:
    """Safely edit message, handling cases where message was deleted or not modified.

    `disable_web_page_preview` is forwarded to edit_message_text when set; omitting
    it keeps Telegram's default (enabled).
    """
    kwargs = {"reply_markup": reply_markup, "parse_mode": parse_mode}
    if disable_web_page_preview is not None:
        kwargs["disable_web_page_preview"] = disable_web_page_preview
    try:
        await query.edit_message_text(text, **kwargs)
        return True
    except BadRequest as e:
        err_msg = str(e).lower()
        if "message is not modified" in err_msg:
            return True  # No change needed, not an error
        if "message to edit not found" in err_msg or "message can't be edited" in err_msg:
            logger.warning(f"Cannot edit message: {e}")
            return False
        raise  # Re-raise unexpected BadRequest


async def _delete_message_after(message, delay: int = 30) -> None:
    """Delete a Telegram message after `delay` seconds. Errors are swallowed
    (message may already be deleted by the user). Used for ephemeral content
    like temporary notices that should auto-cleanup."""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception as e:
        logger.debug(f"_delete_message_after: {e}")


async def check_service_status(service: str) -> bool:
    """Check if systemd service is running."""
    code, _, _ = await sh("systemctl", "is-active", service)
    return code == 0


async def get_telemt_version() -> str:
    """Get telemt version."""
    for command in ("telemt", "/usr/local/bin/telemt", "/usr/bin/telemt"):
        for args in (("--version",), ("-V",)):
            code, stdout, _ = await sh(command, *args, timeout=5)
            if code == 0 and stdout.strip():
                return stdout.strip().split()[-1]
    return "unknown"


def is_docker_running() -> bool:
    """Check if Docker daemon is running."""
    try:
        subprocess.run(
            ["docker", "ps"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return True
    except Exception:
        return False


async def check_old_container() -> Optional[str]:
    """Check for old mtg Docker container (v1 migration)."""
    if not is_docker_running():
        return None
    code, stdout, _ = await sh("docker", "ps", "-a", "--format", "{{.Names}}")
    if code == 0 and "mtg" in stdout:
        return "mtg"
    return None


# ============================================================================
# ACCESS CONTROL
# ============================================================================


def is_user_allowed(user_id: int) -> bool:
    """Check if user ID is in ALLOWED_IDS. If list is empty — waiting for admin."""
    if _WAITING_FOR_ADMIN:
        return False  # Никому не даём доступ пока не назначен админ
    return user_id in ALLOWED_IDS


def add_admin(user_id: int) -> None:
    """Добавить администратора и сохранить в .env."""
    ALLOWED_IDS.add(user_id)
    _save_allowed_ids()
    logger.info(f"Admin added: {user_id}")


def remove_admin(user_id: int) -> None:
    """Убрать администратора и сохранить в .env."""
    ALLOWED_IDS.discard(user_id)
    _save_allowed_ids()
    logger.info(f"Admin removed: {user_id}")


async def require_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check authorization and send error if not allowed."""
    user_id = update.effective_user.id

    # Режим ожидания первого админа — обрабатывается в cmd_start
    if _WAITING_FOR_ADMIN:
        return False

    if not is_user_allowed(user_id):
        if update.message:
            await update.message.reply_text(
                f"⛔ Доступ запрещён.\nВаш ID: <code>{user_id}</code>",
                parse_mode="HTML",
            )
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return False
    return True


# ============================================================================
# MAIN MENU
# ============================================================================


def get_main_menu(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Generate main menu keyboard localized for the given user."""
    buttons = [
        [
            InlineKeyboardButton(_t(user_id, "menu_install"), callback_data="menu_install"),
            InlineKeyboardButton(_t(user_id, "menu_status"), callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_link"), callback_data="menu_link"),
            InlineKeyboardButton(_t(user_id, "menu_share"), callback_data="menu_share"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_restart"), callback_data="menu_restart"),
            InlineKeyboardButton(_t(user_id, "menu_logs"), callback_data="menu_logs"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_change"), callback_data="menu_change"),
            InlineKeyboardButton(_t(user_id, "menu_backup"), callback_data="menu_backup"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_restore"), callback_data="menu_restore"),
            InlineKeyboardButton(_t(user_id, "menu_update"), callback_data="menu_update"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_website"), callback_data="menu_website"),
            InlineKeyboardButton(_t(user_id, "menu_stats"), callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_users"), callback_data="menu_users"),
            InlineKeyboardButton(_t(user_id, "menu_admin_web"), callback_data="menu_admin_web"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_admins"), callback_data="menu_admins"),
            InlineKeyboardButton(_t(user_id, "menu_remove"), callback_data="menu_remove"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_credits"), callback_data="menu_credits"),
            InlineKeyboardButton(_t(user_id, "menu_language"), callback_data="menu_lang"),
        ],
        [
            InlineKeyboardButton(_t(user_id, "menu_close"), callback_data="close_menu"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ============================================================================
# COMMANDS
# ============================================================================


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command - show main menu.

    Если ALLOWED_IDS пуст — режим авто-регистрации первого админа.
    """
    user = update.effective_user
    user_id = user.id

    # ── Режим ожидания первого админа ──
    if _WAITING_FOR_ADMIN:
        name = user.full_name or user.username or str(user_id)
        title = _tf(user_id, "waiting_admin_title", html.escape(name))
        body = _tf(user_id, "waiting_admin_body", user_id)
        text = f"<b>{title}</b>\n\n{body}"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(_t(user_id, "btn_yes"), callback_data=f"admin_confirm_{user_id}"),
                InlineKeyboardButton(_t(user_id, "btn_no"), callback_data="admin_cancel"),
            ]
        ])
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    # ── Проверка доступа ──
    if not is_user_allowed(user_id):
        await update.message.reply_text(
            _tf(user_id, "access_denied", user_id),
            parse_mode="HTML",
        )
        return

    welcome = (
        f"<b>{_tf(user_id, 'welcome_title', PCATELEGRAM_WEB_VERSION)}</b>\n\n"
        f"{_t(user_id, 'welcome_subtitle')}\n"
        f"{_t(user_id, 'welcome_powered')}\n\n"
        f"{_t(user_id, 'welcome_prompt')}"
    )
    await update.message.reply_text(
        welcome, reply_markup=get_main_menu(user_id), parse_mode="HTML"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command - show available commands."""
    if not await require_auth(update, context):
        return
    user_id = _uid(update)
    help_text = (
        f"<b>{_t(user_id, 'help_title')}</b>\n\n"
        f"{_t(user_id, 'help_lines')}"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language picker."""
    if not await require_auth(update, context):
        return
    user_id = _uid(update)
    current = get_user_lang(user_id)
    title = _t(user_id, "lang_title")
    curr_line = _tf(user_id, "lang_current", get_language_name(current))
    prompt = _t(user_id, "lang_choose")
    text = f"<b>{title}</b>\n\n{curr_line}\n\n{prompt}"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_set_en"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_set_ru"),
        ],
        [InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick status check."""
    if not await require_auth(update, context):
        return
    user_id = _uid(update)
    await update.message.reply_text(_t(user_id, "status_checking"), parse_mode="HTML")
    status_text = await get_status_text(user_id)
    await update.message.reply_text(status_text, parse_mode="HTML")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent logs."""
    if not await require_auth(update, context):
        return
    user_id = _uid(update)

    code, stdout, stderr = await sh(
        "journalctl", "-u", TELEMT_SERVICE, "-n", "20", "--no-pager"
    )
    if code == 0:
        log_text = stdout[-1500:] if len(stdout) > 1500 else stdout
        await update.message.reply_text(
            f"<pre>{html.escape(log_text)}</pre>",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(_t(user_id, "logs_failed"))


# ============================================================================
# STATUS
# ============================================================================


async def get_status_text(user_id: Optional[int] = None) -> str:
    """Generate status report (localized)."""
    lines = [f"<b>{_t(user_id, 'status_title')}</b>\n"]

    # Service status
    is_running = await check_service_status(TELEMT_SERVICE)
    running = _t(user_id, "status_running") if is_running else _t(user_id, "status_stopped")
    lines.append(f"<b>{_t(user_id, 'status_service')}:</b> {running}")

    # Telemt version
    version = await get_telemt_version()
    lines.append(f"<b>{_t(user_id, 'status_telemt')}:</b> v{version}")

    # Config status
    config = load_json(PCATELEGRAM_WEB_CONFIG)
    if config:
        lines.append(f"<b>{_t(user_id, 'status_mode')}:</b> {html.escape(str(config.get('mode', 'unknown')))}")
        # install.sh/save_pcatelegram_web_config uses "template_id" (not "template")
        tpl = config.get("template_id") or config.get("template")
        if tpl:
            lines.append(f"<b>{_t(user_id, 'status_template')}:</b> {html.escape(template_display_name(str(tpl)))}")
        if config.get("domain"):
            lines.append(f"<b>{_t(user_id, 'status_domain')}:</b> {html.escape(str(config['domain']))}")
        if config.get("port"):
            lines.append(f"<b>{_t(user_id, 'status_port')}:</b> {html.escape(str(config['port']))}")

    # Telemt config (v3: [server] port = ..., [censorship] tls_domain = ...)
    telemt_cfg = load_toml(TELEMT_CONFIG)
    if telemt_cfg:
        server_cfg = telemt_cfg.get("server", {})
        if "port" in server_cfg:
            lines.append(f"<b>{_t(user_id, 'status_listen_port')}:</b> {server_cfg['port']}")
        censor_cfg = telemt_cfg.get("censorship", {})
        if "tls_domain" in censor_cfg:
            lines.append(f"<b>{_t(user_id, 'status_tls_domain')}:</b> {html.escape(str(censor_cfg['tls_domain']))}")

    # Backups
    backup_count = 0
    try:
        if os.path.exists(BACKUP_DIR):
            backup_count = len([f for f in os.listdir(BACKUP_DIR) if f.endswith((".tar.gz", ".tar.gz.enc")) and not f.endswith(".sha256")])
    except Exception:
        pass
    lines.append(f"<b>Backups:</b> {backup_count}")

    # Old container check
    old_container = await check_old_container()
    if old_container:
        lines.append(f"\n⚠️ <b>Found old container:</b> {html.escape(old_container)}")
        lines.append("Run 'Install' to migrate")

    return "\n".join(lines)


async def get_traffic_stats() -> str:
    """Get formatted traffic statistics."""
    await sh(
        "bash",
        "-lc",
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/stats.sh; "
        "stats_init >/dev/null 2>&1 || true; stats_collect >/dev/null 2>&1 || true",
        timeout=15,
    )

    # Read current snapshot
    current_file = "/run/pcatelegram_web/stats_current.json"
    history_file = "/opt/pcatelegram_web/stats_history.csv"

    try:
        with open(current_file, "r") as f:
            current = json.load(f)
    except Exception:
        return "📊 <b>Статистика</b>\n\n<i>Данные недоступны. Убедитесь что модуль статистики включён.</i>"

    # Read history
    history = []
    try:
        with open(history_file, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    if not row[0].isdigit():
                        continue
                    history.append({
                        "ts": int(row[0]),
                        "proxy": int(row[1]),
                        "site": int(row[2]),
                    })
    except Exception:
        pass

    now = int(time.time())

    def format_bytes(b):
        if b < 1024:
            return f"{b} B"
        if b < 1048576:
            return f"{b/1024:.1f} KB"
        if b < 1073741824:
            return f"{b/1048576:.1f} MB"
        return f"{b/1073741824:.1f} GB"

    def format_rate(bps):
        if bps < 1024:
            return f"{bps:.0f} B/s"
        if bps < 1048576:
            return f"{bps/1024:.1f} KB/s"
        return f"{bps/1048576:.1f} MB/s"

    def calc_for_period(secs, key):
        target_ts = now - secs
        # Find closest snapshot to target_ts
        closest = None
        for h in history:
            if h["ts"] <= target_ts:
                if closest is None or h["ts"] > closest["ts"]:
                    closest = h
        if closest is None:
            return "—", "—"

        current_val = current.get(f"{key}_bytes", 0)
        diff = current_val - closest[key]
        if diff < 0:
            diff = 0
        elapsed = now - closest["ts"]
        if elapsed <= 0:
            elapsed = 1
        rate = diff / elapsed
        return format_bytes(diff), format_rate(rate)

    periods = [
        ("1 мин", 60),
        ("5 мин", 300),
        ("60 мин", 3600),
        ("1 день", 86400),
        ("7 дней", 604800),
        ("30 дней", 2592000),
        ("365 дней", 31536000),
    ]

    lines = ["📊 <b>Статистика трафика</b>\n"]

    for label, key in [("Proxy (telemt)", "proxy"), ("Сайт (nginx)", "site")]:
        lines.append(f"\n<b>{label}:</b>")
        lines.append("<pre>")
        lines.append(f"{'Период':<10} │ {'Трафик':>10} │ {'Скорость':>10}")
        lines.append("─" * 36)
        for name, secs in periods:
            total, rate = calc_for_period(secs, key)
            lines.append(f"{name:<10} │ {total:>10} │ {rate:>10}")
        lines.append("</pre>")

    return "\n".join(lines)


async def cb_menu_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show traffic statistics."""
    query = update.callback_query
    await query.answer()

    stats_text = await get_traffic_stats()

    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="menu_stats")],
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ]

    await safe_edit_message(
        query,
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def cb_menu_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Status callback — show detailed proxy/server status."""
    query = update.callback_query
    await query.answer()

    if not await require_auth(update, context):
        return

    text = await get_status_text(_uid(update))
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="menu_status")],
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ]
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ============================================================================
# INSTALL
# ============================================================================


def get_install_mode_menu(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Install mode selection menu."""
    buttons = [
        [InlineKeyboardButton("⚡ Lite", callback_data="install_mode_lite")],
        [InlineKeyboardButton("🛡 Pro", callback_data="install_mode_pro")],
        [InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(buttons)


async def cb_menu_install(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Install menu callback."""
    query = update.callback_query
    await query.answer()

    # Check for old container
    old_container = await check_old_container()
    if old_container:
        text = (
            f"⚠️ <b>Migration from v1 detected</b>\n\n"
            f"Found Docker container: {html.escape(old_container)}\n\n"
            f"Would you like to:\n"
            f"1. Migrate from v1 (recommended)\n"
            f"2. Fresh install (will remove old container)\n\n"
            f"<i>Select below or choose install mode</i>"
        )
        buttons = [
            [InlineKeyboardButton("🔄 Migrate from v1", callback_data="install_migrate")],
            [InlineKeyboardButton("✨ Fresh Install", callback_data="install_mode_lite")],
            [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
        ]
        keyboard = InlineKeyboardMarkup(buttons)
    else:
        text = "Select installation mode:"
        keyboard = get_install_mode_menu(_uid(update))

    await safe_edit_message(query,
        text, reply_markup=keyboard, parse_mode="HTML"
    )


async def cb_install_mode_lite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lite mode domain selection."""
    query = update.callback_query
    await query.answer()

    # Show domains with pagination (4 per row, 2 rows)
    buttons = []
    for i in range(0, len(LITE_DOMAINS), 2):
        row = []
        for j in range(2):
            if i + j < len(LITE_DOMAINS):
                domain = LITE_DOMAINS[i + j]
                row.append(
                    InlineKeyboardButton(
                        domain, callback_data=f"lite_dom_{i+j}"
                    )
                )
        buttons.append(row)

    buttons.append([InlineKeyboardButton("« Back", callback_data="menu_install")])

    text = "Select a domain for Lite mode:"
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,text, reply_markup=keyboard)


async def cb_lite_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lite domain selection callback — real implementation (v2.4.2+).

    Branches on current mode:
      * lite mode (active): invoke `install.sh --action=change-lite-domain`
        which regenerates the telemt TOML with a new fake-TLS mask domain and
        restarts the service. Preserves secret/port.
      * any other mode: route to CLI. Fresh Lite install is interactive.
    """
    query = update.callback_query
    data = query.data
    try:
        domain_idx = int(data.split("_")[-1])
        domain = LITE_DOMAINS[domain_idx]
    except (ValueError, IndexError):
        await query.answer("Invalid domain selection")
        return

    # Defense-in-depth: LITE_DOMAINS is trusted, but validate the shape anyway
    # in case someone extends the list with garbage later.
    if not _DOMAIN_RE.match(domain):
        logger.warning(f"cb_lite_domain: rejecting malformed domain {domain!r}")
        await query.answer("Invalid domain")
        return

    await query.answer()

    config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
    current_mode = config.get("mode", "")

    if current_mode != "lite":
        text = (
            "<b>⚠️ Установка Lite из бота пока не поддерживается</b>\n\n"
            f"Выбранный домен: <code>{html.escape(domain)}</code>\n\n"
            "Чтобы установить Lite, запустите на сервере:\n"
            "<code>pcatelegram_web</code> → <b>1) Прокси → 1) Установить/Обновить → Lite</b>\n\n"
            "Существующая конфигурация <b>не была изменена</b>."
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
        )
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")
        return

    # Lite active — switch fake-TLS mask domain in place
    if _BOT_ACTION_LOCK.locked():
        await safe_edit_message(
            query,
            "<b>⏳ Другая операция уже выполняется</b>\n\n"
            "Дождитесь завершения предыдущей смены шаблона/домена и повторите.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
            ),
            parse_mode="HTML",
        )
        return

    progress_text = (
        "<b>⏳ Меняю маскировочный домен...</b>\n\n"
        f"Новый домен: <code>{html.escape(domain)}</code>\n\n"
        "Перегенерирую конфиг telemt и перезапускаю сервис."
    )
    await safe_edit_message(query, progress_text, parse_mode="HTML")

    async with _BOT_ACTION_LOCK:
        result = await run_bot_action("change-lite-domain", timeout=30, domain=domain)

    if result.get("status") == "success":
        text = (
            "<b>✅ Маскировочный домен обновлён</b>\n\n"
            f"Новый домен: <code>{html.escape(domain)}</code>\n\n"
            "telemt перезапущен. <b>Важно:</b> старые ссылки подключения больше "
            "не будут работать — нужно заново раздать новые."
        )
    else:
        err_msg = result.get("message", "unknown error")
        err_code = result.get("code", "")
        text = (
            "<b>❌ Не удалось сменить домен</b>\n\n"
            f"Домен: <code>{html.escape(domain)}</code>\n"
            f"Причина: <code>{html.escape(err_msg)}</code>"
            + (f" (<code>{html.escape(err_code)}</code>)" if err_code else "")
            + "\n\n"
            "Существующая конфигурация <b>не была изменена</b>."
        )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")


async def cb_install_mode_pro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pro mode - show template categories."""
    query = update.callback_query
    await query.answer()

    catalog = load_json(TEMPLATES_CATALOG)
    if not catalog or "categories" not in catalog:
        await safe_edit_message(query,
            "❌ Template catalog not found",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back", callback_data="menu_install")]]
            ),
        )
        return

    user_id = _uid(update)
    buttons = []
    # First item: custom git template (matches CLI behaviour)
    buttons.append([InlineKeyboardButton(
        _t(user_id, "cg_title"), callback_data="pro_custom_git"
    )])
    for cat in catalog.get("categories", []):
        buttons.append(
            [
                InlineKeyboardButton(
                    f"📁 {cat['name']}", callback_data=f"pro_cat_{cat['id']}"
                )
            ]
        )
    buttons.append([InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_install")])

    text = "Pro Mode — Select Template Category:"
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query, text, reply_markup=keyboard)


# ── Custom git template input flow ──────────────────────────────────────────
_CUSTOM_GIT_WAITERS: Dict[int, bool] = {}
_CUSTOM_GIT_URL_RE = re.compile(r'^https://[A-Za-z0-9._~:/\-?#\[\]@!$&\'()*+,;=%]+(@[A-Za-z0-9._\-/]+)?$')
_CUSTOM_GIT_MAX_MB = 100
_CUSTOM_GIT_CLONE_TIMEOUT = 90


def _validate_custom_git_url(url: str) -> bool:
    if not url or len(url) > 512:
        return False
    # Block shell metacharacters explicitly
    for bad in (" ", "`", "$", "(", ")", "<", ">", "|", "\\", "\t", "\n", "\r", ";", "&", "'", '"'):
        if bad in url:
            return False
    if not url.lower().startswith("https://"):
        return False
    # Reject embedded userinfo (https://user:pass@host/...) to prevent credential leakage.
    # We look at the netloc — anything between https:// and the first '/'.
    rest = url[len("https://"):]
    netloc_end = rest.find("/")
    netloc = rest if netloc_end == -1 else rest[:netloc_end]
    if "@" in netloc:
        return False
    # Hostname sanity: no empty host, no whitespace already blocked above
    if not netloc or netloc.startswith(":") or netloc.endswith(":"):
        return False
    return True


async def _download_custom_git_template(url_with_branch: str) -> Tuple[bool, str, str]:
    """Clone a custom git repo and stage its static site under WEBSITE_ROOT.

    Returns (ok, tpl_id, message_key_or_path).
    """
    # Parse @branch suffix (only when the branch appears on the last path segment)
    branch = None
    url = url_with_branch
    if "@" in url_with_branch.rsplit("/", 1)[-1]:
        base, _, maybe_branch = url_with_branch.rpartition("@")
        if (
            base.lower().startswith("https://")
            and maybe_branch  # reject empty branch after `@`
            and "/" not in maybe_branch
            and re.match(r'^[A-Za-z0-9._/\-]+$', maybe_branch)
        ):
            url = base
            branch = maybe_branch
        elif not maybe_branch and base.lower().startswith("https://"):
            # Trailing `@` with no branch — drop it so git doesn't treat it as userinfo
            url = base

    tpl_id = "custom_" + hashlib.md5(url_with_branch.encode("utf-8")).hexdigest()[:10]
    target_dir = f"/opt/pcatelegram_web/custom_templates/{tpl_id}"

    # Clean previous copy
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)

    tmp_dir = f"/tmp/{tpl_id}_clone"
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [url, tmp_dir]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=_CUSTOM_GIT_CLONE_TIMEOUT)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return False, tpl_id, "cg_timeout"
        if proc.returncode != 0:
            return False, tpl_id, "cg_invalid"
    except Exception as e:
        logger.warning("custom git clone failed: %s", e)
        return False, tpl_id, "cg_invalid"

    # Remove .git to enforce size guard and avoid leaking repo history
    git_dir = os.path.join(tmp_dir, ".git")
    if os.path.isdir(git_dir):
        shutil.rmtree(git_dir, ignore_errors=True)

    # Size guard
    total = 0
    for root, _dirs, files in os.walk(tmp_dir):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    if total > _CUSTOM_GIT_MAX_MB * 1024 * 1024:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False, tpl_id, "cg_too_big"

    # Locate index.html in priority order
    found_root = None
    for sub in ("", "dist", "public", "build", "_site", "site", "docs", "out", "www"):
        cand = os.path.join(tmp_dir, sub) if sub else tmp_dir
        if os.path.isfile(os.path.join(cand, "index.html")):
            found_root = cand
            break
    if not found_root:
        # Fallback: search maxdepth 4
        for root, _dirs, files in os.walk(tmp_dir):
            depth = root[len(tmp_dir):].count(os.sep)
            if depth > 4:
                continue
            if "index.html" in files:
                found_root = root
                break
    if not found_root:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False, tpl_id, "cg_no_index"

    # Stage final template dir
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    shutil.copytree(found_root, target_dir)
    try:
        with open(os.path.join(target_dir, ".custom_git_source"), "w", encoding="utf-8") as f:
            f.write(url_with_branch + "\n")
    except OSError:
        pass
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return True, tpl_id, target_dir


async def cb_pro_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show templates in category."""
    query = update.callback_query
    data = query.data
    cat_id = data.removeprefix("pro_cat_")

    await query.answer()

    catalog = load_json(TEMPLATES_CATALOG)
    if not catalog:
        await safe_edit_message(query,"❌ Template catalog not found")
        return

    # Find category and templates
    category = None
    templates = []
    for cat in catalog.get("categories", []):
        if cat["id"] == cat_id:
            category = cat
            templates = cat.get("templates", [])
            break

    if not category:
        await safe_edit_message(query,"❌ Category not found")
        return

    buttons = []
    for tpl in templates:
        key = pro_template_key_for_id(context, tpl["id"])
        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎨 {tpl['name']}", callback_data=f"pro_tpl_{key}"
                )
            ]
        )
    buttons.append([InlineKeyboardButton("« Back", callback_data="install_mode_pro")])

    text = f"Select template from <b>{html.escape(category['name'])}</b>:"
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_pro_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show template preview and confirm."""
    query = update.callback_query
    data = query.data
    tpl_key = data.removeprefix("pro_tpl_")
    tpl_id = resolve_pro_template_id(context, tpl_key)

    await query.answer()

    catalog = load_json(TEMPLATES_CATALOG)
    if not catalog:
        await safe_edit_message(query,"❌ Template catalog not found")
        return

    # Find template
    template = None
    for cat in catalog.get("categories", []):
        for tpl in cat.get("templates", []):
            if tpl["id"] == tpl_id:
                template = tpl
                break
        if template:
            break

    if not template:
        await safe_edit_message(query,"❌ Template not found")
        return

    tpl_name = html.escape(template.get('name', 'Unknown'))
    tpl_desc = html.escape(template.get('description', 'N/A'))
    text = (
        f"<b>🎨 Template Preview</b>\n\n"
        f"<b>Name:</b> {tpl_name}\n"
        f"<b>Description:</b> {tpl_desc}\n\n"
    )
    if "preview_url" in template:
        preview_url = html.escape(template['preview_url'], quote=True)
        text += f'<a href="{preview_url}">View Live Preview</a>\n\n'

    text += "Confirm installation?"

    buttons = [
        [
            InlineKeyboardButton(
                "✅ Install", callback_data=f"pro_confirm_{pro_template_key_for_id(context, tpl_id)}"
            )
        ],
        [InlineKeyboardButton("« Back", callback_data="install_mode_pro")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_pro_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm Pro template selection — real implementation (v2.4.2+).

    Branches on current mode:
      * pro mode (active deployment): invoke `install.sh --action=change-template`
        which downloads the new template and redeploys it to nginx. Reuses the
        existing domain + SSL cert.
      * any other mode (or no install at all): route to CLI. Fresh Pro install
        still requires interactive flow (domain, email, DNS check) — not safe
        to run headless from the bot.

    Historic context: v2.4.1 stub used to overwrite config.json with a fake
    blob; that was replaced with a safe message in v2.4.1 hotfix; now in
    v2.4.2 we wire the real change-template path through install.sh.
    """
    query = update.callback_query
    data = query.data
    tpl_key = data.removeprefix("pro_confirm_")
    tpl_id = resolve_pro_template_id(context, tpl_key)

    await query.answer()

    # Defense-in-depth: even though subprocess.exec uses list args (no shell),
    # we still enforce the catalog id shape before handing it to install.sh.
    if not _TPL_ID_RE.match(tpl_id):
        logger.warning(f"cb_pro_confirm: rejecting malformed tpl_id {tpl_id!r}")
        await safe_edit_message(
            query,
            "<b>❌ Некорректный идентификатор шаблона</b>\n\n"
            "Выбран неподдерживаемый шаблон. Вернитесь в меню и попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
            ),
            parse_mode="HTML",
        )
        return

    # Read current config to decide: in-place change-template vs fresh install
    config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
    current_mode = config.get("mode", "")

    if current_mode != "pro":
        # Fresh install / mode switch — still routes to CLI (needs domain, SSL)
        text = (
            "<b>⚠️ Установка Pro из бота пока не поддерживается</b>\n\n"
            f"Выбранный шаблон: <code>{html.escape(tpl_id)}</code>\n\n"
            "Pro-режим требует ввода домена, email и проверки DNS. "
            "Чтобы установить Pro, запустите на сервере:\n"
            "<code>pcatelegram_web</code> → <b>1) Прокси → 1) Установить/Обновить → Pro</b>\n\n"
            "Существующая конфигурация <b>не была изменена</b>."
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
        )
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")
        return

    # Pro mode is active — perform change-template in place
    if _BOT_ACTION_LOCK.locked():
        await safe_edit_message(
            query,
            "<b>⏳ Другая операция уже выполняется</b>\n\n"
            "Дождитесь завершения предыдущей смены шаблона/домена и повторите.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
            ),
            parse_mode="HTML",
        )
        return

    progress_text = (
        "<b>⏳ Меняю шаблон сайта...</b>\n\n"
        f"Шаблон: <code>{html.escape(tpl_id)}</code>\n\n"
        "Скачиваю репозиторий и разворачиваю в nginx. "
        "Это может занять 30–90 секунд."
    )
    await safe_edit_message(query, progress_text, parse_mode="HTML")

    # Template download + git clone can be slow — generous timeout.
    # Mutex serializes with any concurrent change-lite-domain/change-template.
    async with _BOT_ACTION_LOCK:
        result = await run_bot_action("change-template", timeout=180, template=tpl_id)

    if result.get("status") == "success":
        domain = result.get("domain", config.get("domain", ""))
        text = (
            "<b>✅ Шаблон обновлён</b>\n\n"
            f"Новый шаблон: <code>{html.escape(tpl_id)}</code>\n"
            f"Сайт: <a href=\"https://{html.escape(domain, quote=True)}\">https://{html.escape(domain)}</a>\n\n"
            "Прокси продолжает работать без перерыва."
        )
    else:
        err_msg = result.get("message", "unknown error")
        err_code = result.get("code", "")
        text = (
            "<b>❌ Не удалось сменить шаблон</b>\n\n"
            f"Шаблон: <code>{html.escape(tpl_id)}</code>\n"
            f"Причина: <code>{html.escape(err_msg)}</code>"
            + (f" (<code>{html.escape(err_code)}</code>)" if err_code else "")
            + "\n\n"
            "Существующая конфигурация <b>не была изменена</b>. "
            "Попробуйте другой шаблон или запустите <code>pcatelegram_web</code> из консоли."
        )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)


# ============================================================================
# PROXY LINK & SHARE
# ============================================================================

def quote_toml_key(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def ordered_user_lines(users: Dict[str, str]) -> List[str]:
    names: List[str] = []
    if "main" in users:
        names.append("main")
    names.extend(sorted(name for name in users if name != "main"))
    return [f'{quote_toml_key(name)} = "{users[name]}"' for name in names]


def ordered_user_int_lines(values: Dict[str, int]) -> List[str]:
    positive: Dict[str, int] = {}
    for name, value in values.items():
        name_s = str(name)
        if not _USER_NAME_RE.match(name_s):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            positive[name_s] = number
    names: List[str] = []
    if "main" in positive:
        names.append("main")
    names.extend(sorted(name for name in positive if name != "main"))
    return [f'{quote_toml_key(name)} = {positive[name]}' for name in names]


def load_telemt_users() -> Dict[str, str]:
    """Return users from [access.users] in telemt config."""
    telemt_cfg = load_toml(TELEMT_CONFIG) or {}
    users = telemt_cfg.get("access", {}).get("users", {})
    if not isinstance(users, dict):
        return {}
    return {
        str(name): str(secret)
        for name, secret in users.items()
        if isinstance(name, str) and isinstance(secret, str)
    }


def load_user_max_unique_ips() -> Dict[str, int]:
    telemt_cfg = load_toml(TELEMT_CONFIG) or {}
    limits = telemt_cfg.get("access", {}).get("user_max_unique_ips", {})
    if not isinstance(limits, dict):
        return {}
    clean: Dict[str, int] = {}
    for name, value in limits.items():
        name_s = str(name)
        if not _USER_NAME_RE.match(name_s):
            continue
        try:
            clean[name_s] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return clean


def load_disabled_users() -> Dict[str, str]:
    raw = load_json(DISABLED_USERS_FILE) or {}
    if not isinstance(raw, dict):
        return {}
    users = raw.get("users") if isinstance(raw.get("users"), dict) else raw
    if not isinstance(users, dict):
        return {}
    clean: Dict[str, str] = {}
    for name, secret in users.items():
        if name in {"version", "updated_at"}:
            continue
        name_s = str(name).strip()
        secret_s = str(secret or "").strip()
        if _USER_NAME_RE.match(name_s) and secret_s:
            clean[name_s] = secret_s
    return clean


def save_disabled_users(users: Dict[str, str]) -> bool:
    payload = {
        "version": 1,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "users": {name: users[name] for name in sorted(users)},
    }
    ok = save_json(DISABLED_USERS_FILE, payload)
    if ok:
        try:
            os.chmod(DISABLED_USERS_FILE, 0o600)
        except OSError:
            pass
    return ok


def load_user_records() -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    limits = load_user_max_unique_ips()
    for name, secret in load_disabled_users().items():
        records[name] = {"secret": secret, "enabled": False, "max_unique_ips": limits.get(name, 0)}
    for name, secret in load_telemt_users().items():
        records[name] = {"secret": secret, "enabled": True, "max_unique_ips": limits.get(name, 0)}
    return records


def save_toml_int_table(table: str, values: Dict[str, int]) -> bool:
    try:
        os.makedirs(os.path.dirname(TELEMT_CONFIG), exist_ok=True)
        if os.path.exists(TELEMT_CONFIG):
            with open(TELEMT_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
        else:
            lines = []
        rendered = ordered_user_int_lines(values)
        header = f"[{table}]"
        out: List[str] = []
        in_table = False
        found = False
        for raw in lines:
            if raw.strip() == header:
                found = True
                in_table = True
                if rendered:
                    out.append(raw)
                    out.extend(rendered)
                continue
            if in_table and raw.strip().startswith("["):
                in_table = False
            if in_table:
                continue
            out.append(raw)
        if not found and rendered:
            if out and out[-1].strip():
                out.append("")
            out.append(header)
            out.extend(rendered)
        tmp = f"{TELEMT_CONFIG}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(out).rstrip() + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, TELEMT_CONFIG)
        return True
    except Exception as e:
        logger.error(f"Failed to save telemt int table {table}: {e}")
        return False


def save_user_max_unique_ips(values: Dict[str, int]) -> bool:
    return save_toml_int_table("access.user_max_unique_ips", values)


def normalize_max_unique_ips(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("Лимит должен быть целым числом")
    if number < 0 or number > MAX_UNIQUE_IP_LIMIT:
        raise ValueError(f"Лимит должен быть от 0 до {MAX_UNIQUE_IP_LIMIT}")
    return number


def save_telemt_users(users: Dict[str, str]) -> bool:
    """Persist [access.users] while keeping the rest of the TOML structure."""
    try:
        os.makedirs(os.path.dirname(TELEMT_CONFIG), exist_ok=True)
        if os.path.exists(TELEMT_CONFIG):
            with open(TELEMT_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
        else:
            lines = []
        rendered = ordered_user_lines(users)
        out: List[str] = []
        in_users = False
        found = False
        for raw in lines:
            if raw.strip() == "[access.users]":
                found = True
                in_users = True
                out.append(raw)
                out.extend(rendered)
                continue
            if in_users and raw.strip().startswith("["):
                in_users = False
            if in_users:
                continue
            out.append(raw)
        if not found:
            if out and out[-1].strip():
                out.append("")
            out.append("[access.users]")
            out.extend(rendered)
        tmp = f"{TELEMT_CONFIG}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(out).rstrip() + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, TELEMT_CONFIG)
        return True
    except Exception as e:
        logger.error(f"Failed to save telemt users: {e}")
        return False


async def refresh_telemt_after_user_change() -> bool:
    """Restart telemt after config user changes, coalescing rapid UI clicks."""
    global _LAST_TELEMT_RESTART
    now = time.monotonic()
    if _LAST_TELEMT_RESTART > 0 and now - _LAST_TELEMT_RESTART < TELEMT_RESTART_DEBOUNCE_SECONDS:
        code, stdout, _ = await sh("systemctl", "is-active", TELEMT_SERVICE, timeout=5)
        if code == 0 and stdout.strip() == "active":
            return True
    await sh("systemctl", "reset-failed", TELEMT_SERVICE, timeout=5)
    _LAST_TELEMT_RESTART = now
    code, _, _ = await sh("systemctl", "--no-block", "restart", TELEMT_SERVICE, timeout=5)
    return code == 0


async def telemt_api_get(path: str) -> Optional[Dict[str, Any]]:
    """Read telemt local API if it is enabled in config."""
    code, stdout, _ = await sh(
        "curl",
        "-sS",
        "--max-time",
        "3",
        f"http://127.0.0.1:9091{path}",
        timeout=5,
    )
    if code != 0 or not stdout.strip():
        return None
    try:
        data = json.loads(stdout)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_traffic_value(data: Any, keys: List[str]) -> int:
    if isinstance(data, dict):
        total = 0
        for key, value in data.items():
            if key in keys and isinstance(value, (int, float)):
                total += int(value)
            elif isinstance(value, (dict, list)):
                total += _extract_traffic_value(value, keys)
        return total
    if isinstance(data, list):
        return sum(_extract_traffic_value(item, keys) for item in data)
    return 0


def user_traffic_history_summary(name: str) -> str:
    rows: List[Dict[str, int]] = []
    try:
        with open(USER_STATS_HISTORY, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            previous = None
            for row in reader:
                if row.get("user") != name:
                    continue
                try:
                    item = {
                        "epoch": int(row.get("epoch") or 0),
                        "total_octets": int(row.get("total_octets") or 0),
                    }
                except ValueError:
                    continue
                item["total_delta"] = max(0, item["total_octets"] - previous["total_octets"]) if previous else 0
                rows.append(item)
                previous = item
    except Exception:
        rows = []

    if not rows:
        return "\n<i>История по ключу пока не накоплена.</i>"

    latest = max(row["epoch"] for row in rows)
    periods = [("15 мин", 15 * 60), ("1 час", 60 * 60), ("24 часа", 24 * 60 * 60), ("Месяц", 30 * 24 * 60 * 60)]
    lines = ["\n<b>История трафика:</b>", "<pre>", f"{'Период':<8} │ {'Трафик':>10}", "─" * 23]
    for label, seconds in periods:
        window = [row for row in rows if row["epoch"] >= latest - seconds]
        total = sum(max(0, row.get("total_delta", 0)) for row in window)
        lines.append(f"{label:<8} │ {format_bytes_human(total):>10}")
    lines.append("</pre>")
    return "\n".join(lines)


async def get_proxy_link_for_secret(secret: str) -> Optional[str]:
    """Generate a fake-TLS proxy link for an arbitrary telemt user secret."""
    config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
    if not secret:
        return None

    mode = config.get("mode", "lite")
    domain = config.get("domain", "")
    port = config.get("port", 443)

    if mode == "pro" and domain:
        domain_hex = str(domain).encode().hex()
        return f"tg://proxy?server={domain}&port={port}&secret=ee{secret}{domain_hex}"

    code, stdout, _ = await sh("curl", "-s", "-4", "--max-time", "5", "https://api.ipify.org")
    server = stdout.strip() if code == 0 and stdout.strip() else "0.0.0.0"
    mask_host = config.get("mask_host", "")
    if mask_host:
        domain_hex = str(mask_host).encode().hex()
        return f"tg://proxy?server={server}&port={port}&secret=ee{secret}{domain_hex}"
    return f"tg://proxy?server={server}&port={port}&secret={secret}"


async def get_proxy_link() -> Optional[str]:
    """Generate proxy link from config. Pro-mode uses domain + fake-TLS secret."""
    config = load_json(PCATELEGRAM_WEB_CONFIG)
    if not config:
        return None

    # Get secret from telemt TOML config (v3 format: [access.users] main = "...")
    secret = config.get("secret", "")
    if not secret:
        telemt_cfg = load_toml(TELEMT_CONFIG)
        if telemt_cfg:
            access = telemt_cfg.get("access", {})
            users = access.get("users", {})
            if isinstance(users, dict):
                secret = users.get("main", "")
    if not secret:
        return None

    return await get_proxy_link_for_secret(secret)


async def cb_menu_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and show proxy link."""
    query = update.callback_query
    await query.answer()

    link = await get_proxy_link()
    if not link:
        text = "❌ Proxy not installed yet. Run install first."
    else:
        text = (
            f"<b>🔗 Proxy Link</b>\n\n"
            f"<code>{html.escape(link)}</code>\n\n"
            f"Open in Telegram to connect."
        )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_menu_share(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Share link as QR code."""
    query = update.callback_query
    await query.answer()

    link = await get_proxy_link()
    if not link:
        text = "❌ Proxy not installed yet."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
        )
        await safe_edit_message(query,text, reply_markup=keyboard)
        return

    # Try to generate QR code
    qr_file = None
    code, _, _ = await sh("which", "qrencode")
    if code == 0:
        qr_path = "/tmp/proxy_qr.png"
        code, _, _ = await sh("qrencode", "-o", qr_path, link)
        if code == 0 and os.path.exists(qr_path):
            qr_file = qr_path

    if qr_file:
        try:
            with open(qr_file, "rb") as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"<b>📤 Proxy QR Code</b>\n\n{html.escape(link)}",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Failed to send QR code: {e}")
            await safe_edit_message(query,
                f"<b>🔗 Proxy Link</b>\n\n<code>{html.escape(link)}</code>",
                parse_mode="HTML",
            )
        finally:
            try:
                os.remove(qr_file)
            except OSError:
                pass
    else:
        await safe_edit_message(query,
            f"<b>🔗 Proxy Link</b>\n\n<code>{html.escape(link)}</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
            ),
            parse_mode="HTML",
        )


# ============================================================================
# TELEMT USERS
# ============================================================================


def _users_keyboard(users: Dict[str, Dict[str, Any]], user_id: Optional[int]) -> InlineKeyboardMarkup:
    rows = []
    for name in sorted(users, key=lambda item: (item != "main", item)):
        enabled = bool(users[name].get("enabled"))
        icon = "🟢" if enabled else "⏸"
        rows.append([InlineKeyboardButton(f"{icon} {name}", callback_data=f"user_view_{name}")])
    rows.append([InlineKeyboardButton("➕ Добавить ключ", callback_data="user_add")])
    rows.append([
        InlineKeyboardButton(_t(user_id, "btn_refresh"), callback_data="menu_users"),
        InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main"),
    ])
    return InlineKeyboardMarkup(rows)


async def cb_menu_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    users = load_user_records()

    if users:
        user_lines = "\n".join(
            f"{'🟢' if users[name].get('enabled') else '⏸'} <code>{html.escape(name)}</code>"
            for name in sorted(users, key=lambda item: (item != "main", item))
        )
    else:
        user_lines = "<i>Ключей пока нет</i>"

    api_summary = await telemt_api_get("/v1/stats/summary")
    api_note = ""
    if api_summary and isinstance(api_summary.get("data"), dict):
        data = api_summary["data"]
        configured = data.get("configured_users")
        active = data.get("active_connections") or data.get("connections_active")
        bits = []
        if configured is not None:
            bits.append(f"users: <code>{configured}</code>")
        if active is not None:
            bits.append(f"active: <code>{active}</code>")
        if bits:
            api_note = "\n\nAPI: " + ", ".join(bits)

    text = (
        "<b>🔑 Ключи пользователей</b>\n\n"
        f"{user_lines}"
        f"{api_note}\n\n"
        "<i>Нажмите на пользователя, чтобы увидеть ссылку, статистику и действия.</i>"
    )
    await safe_edit_message(query, text, reply_markup=_users_keyboard(users, user_id), parse_mode="HTML")


async def _user_detail_text(name: str, secret: str, enabled: bool = True, max_unique_ips: int = 0) -> str:
    link = await get_proxy_link_for_secret(secret)
    api = await telemt_api_get(f"/v1/users/{quote(name, safe='')}") if enabled else None
    details = ""
    if api:
        data = api.get("data", api)
        total = int(data.get("total_octets") or 0) if isinstance(data, dict) else 0
        conns = int(data.get("current_connections") or 0) if isinstance(data, dict) else 0
        active_ips = int(data.get("active_unique_ips") or 0) if isinstance(data, dict) else 0
        recent_ips = int(data.get("recent_unique_ips") or 0) if isinstance(data, dict) else 0
        parts = []
        parts.append(f"Трафик всего: <b>{format_bytes_human(total)}</b>")
        parts.append(f"Подключения: <code>{conns}</code>")
        parts.append(f"Активные IP: <code>{active_ips}</code>")
        if recent_ips:
            parts.append(f"Недавние IP: <code>{recent_ips}</code>")
        if parts:
            details = "\n" + "\n".join(parts)
        else:
            compact = json.dumps(data, ensure_ascii=False)[:600]
            details = f"\n<pre>{html.escape(compact)}</pre>"
    elif enabled:
        details = "\n<i>Runtime API недоступен. Новые установки PCAtelegram_web включают его автоматически.</i>"
    else:
        details = "\n<i>Ключ отключён и сейчас не принимается telemt.</i>"
    details += user_traffic_history_summary(name)

    link_line = html.escape(link) if link else "link unavailable"
    status_line = "🟢 enabled" if enabled else "⏸ disabled"
    limit_line = "0 (безлимит)" if not max_unique_ips else str(max_unique_ips)
    return (
        f"<b>👤 {html.escape(name)}</b>\n\n"
        f"Status: <b>{status_line}</b>\n"
        f"Лимит IP: <code>{html.escape(limit_line)}</code>\n"
        f"Secret: <code>{html.escape(secret)}</code>\n\n"
        f"<b>Ссылка:</b>\n<code>{link_line}</code>\n"
        f"{details}"
    )


async def cb_user_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_view_")
    users = load_user_records()
    record = users.get(name)
    if not record:
        await safe_edit_message(
            query,
            "❌ Пользователь не найден.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_users")]]),
        )
        return
    enabled = bool(record.get("enabled"))
    secret = str(record.get("secret", ""))
    max_unique_ips = int(record.get("max_unique_ips") or 0)

    buttons = [
        [InlineKeyboardButton("⏸ Отключить" if enabled else "▶️ Включить", callback_data=f"user_toggle_{name}")],
        [InlineKeyboardButton("🌐 Лимит IP", callback_data=f"user_ip_limit_{name}")],
        [InlineKeyboardButton("📷 QR", callback_data=f"user_qr_{name}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"user_del_{name}")],
        [InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_users")],
    ]
    if name == "main":
        buttons = [
            [InlineKeyboardButton("🔒 Main key", callback_data=f"user_view_{name}")],
            [InlineKeyboardButton("🌐 Лимит IP", callback_data=f"user_ip_limit_{name}")],
            [InlineKeyboardButton("📷 QR", callback_data=f"user_qr_{name}")],
            [InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_users")],
        ]
    await safe_edit_message(
        query,
        await _user_detail_text(name, secret, enabled, max_unique_ips),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cb_user_qr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_qr_")
    users = load_user_records()
    record = users.get(name)
    if not record:
        await query.answer("Ключ не найден", show_alert=True)
        return
    link = await get_proxy_link_for_secret(str(record.get("secret", "")))
    if not link:
        await query.answer("Ссылка недоступна", show_alert=True)
        return

    qr_file = f"/tmp/pcatelegram_web_user_qr_{hashlib.sha256(name.encode()).hexdigest()[:10]}.png"
    code, _, _ = await sh("which", "qrencode")
    if code == 0:
        code, _, _ = await sh("qrencode", "-o", qr_file, link)
    if code == 0 and os.path.exists(qr_file):
        try:
            with open(qr_file, "rb") as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"<b>📷 QR: {html.escape(name)}</b>\n\n<code>{html.escape(link)}</code>",
                    parse_mode="HTML",
                )
        finally:
            try:
                os.remove(qr_file)
            except OSError:
                pass
    else:
        await safe_edit_message(
            query,
            f"<b>🔗 {html.escape(name)}</b>\n\n<code>{html.escape(link)}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data=f"user_view_{name}")]]),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


async def cb_user_ip_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_ip_limit_")
    users = load_user_records()
    record = users.get(name)
    if not record:
        await query.answer("Ключ не найден", show_alert=True)
        return
    current = int(record.get("max_unique_ips") or 0)
    context.user_data["awaiting_user_ip_limit"] = name
    text = (
        f"<b>🌐 Лимит IP: {html.escape(name)}</b>\n\n"
        f"Текущее значение: <code>{current}</code>\n"
        "Отправьте число: <code>0</code> — безлимит, <code>1</code> — только один активный IP, "
        "<code>2</code> — два активных IP и так далее."
    )
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_cancel"), callback_data=f"user_view_{name}")]]),
        parse_mode="HTML",
    )


async def set_user_ip_limit_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_value: str, name: str) -> None:
    user_id = update.effective_user.id
    try:
        limit = normalize_max_unique_ips(raw_value.strip())
    except ValueError as exc:
        await update.message.reply_text(f"❌ {html.escape(str(exc))}", parse_mode="HTML")
        return
    with FileLock(USER_LOCK_FILE):
        records = load_user_records()
        if name not in records:
            await update.message.reply_text("❌ Ключ не найден.")
            return
        limits = load_user_max_unique_ips()
        if limit > 0:
            limits[name] = limit
        else:
            limits.pop(name, None)
        saved = save_user_max_unique_ips(limits)
    if not saved:
        await update.message.reply_text("❌ Не удалось сохранить /etc/telemt/config.toml")
        return
    await refresh_telemt_after_user_change()
    await update.message.reply_text(
        f"✅ Лимит IP сохранён для <code>{html.escape(name)}</code>: <code>{limit}</code>",
        reply_markup=_users_keyboard(load_user_records(), user_id),
        parse_mode="HTML",
    )


async def cb_user_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    context.user_data["awaiting_user_name"] = True
    text = (
        "<b>➕ Новый ключ</b>\n\n"
        "Отправьте имя пользователя: латиница, цифры, <code>_ . -</code>, до 48 символов.\n"
        "Пример: <code>ivan</code> или <code>family-1</code>."
    )
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_cancel"), callback_data="menu_users")]]),
        parse_mode="HTML",
    )


async def cb_user_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_toggle_")
    if name == "main":
        await query.answer("main нельзя отключить", show_alert=True)
        return
    with FileLock(USER_LOCK_FILE):
        active = load_telemt_users()
        disabled = load_disabled_users()
        records = load_user_records()
        record = records.get(name)
        if not record:
            await query.answer("Ключ не найден", show_alert=True)
            return
        enabled = not bool(record.get("enabled"))
        secret = str(record.get("secret", ""))
        if enabled:
            disabled.pop(name, None)
            active[name] = secret
        else:
            active.pop(name, None)
            disabled[name] = secret
        if enabled:
            saved = save_telemt_users(active) and save_disabled_users(disabled)
        else:
            saved = save_disabled_users(disabled) and save_telemt_users(active)
    if not saved:
        await safe_edit_message(query, "❌ Не удалось сохранить состояние ключа")
        return
    await refresh_telemt_after_user_change()
    await safe_edit_message(
        query,
        f"{'✅ Ключ включён' if enabled else '⏸ Ключ отключён'}: <code>{html.escape(name)}</code>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data=f"user_view_{name}")]]),
        parse_mode="HTML",
    )


async def cb_user_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_del_")
    if name == "main":
        await query.answer("main нельзя удалить", show_alert=True)
        return
    text = f"Удалить ключ <code>{html.escape(name)}</code>?"
    buttons = [
        [InlineKeyboardButton("✅ Удалить", callback_data=f"user_del_yes_{name}")],
        [InlineKeyboardButton(_t(user_id, "btn_cancel"), callback_data=f"user_view_{name}")],
    ]
    await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def cb_user_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    name = query.data.removeprefix("user_del_yes_")
    with FileLock(USER_LOCK_FILE):
        active = load_telemt_users()
        disabled = load_disabled_users()
        records = load_user_records()
        if name == "main" or name not in records:
            await query.answer("Нельзя удалить этот ключ", show_alert=True)
            return
        active.pop(name, None)
        disabled.pop(name, None)
        limits = load_user_max_unique_ips()
        limits.pop(name, None)
        saved = save_telemt_users(active) and save_disabled_users(disabled) and save_user_max_unique_ips(limits)
    if not saved:
        await safe_edit_message(query, "❌ Не удалось сохранить config.toml")
        return
    await refresh_telemt_after_user_change()
    await safe_edit_message(
        query,
        f"✅ Ключ <code>{html.escape(name)}</code> удалён.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_users")]]),
        parse_mode="HTML",
    )


async def create_user_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    user_id = update.effective_user.id
    if not _USER_NAME_RE.match(name):
        await update.message.reply_text("❌ Некорректное имя. Используйте латиницу, цифры, _ . - и до 48 символов.")
        return
    with FileLock(USER_LOCK_FILE):
        records = load_user_records()
        if name in records:
            await update.message.reply_text("❌ Такой пользователь уже есть.")
            return
        users = load_telemt_users()
        secret = hashlib.sha256(f"{name}:{time.time()}:{os.urandom(16).hex()}".encode()).hexdigest()[:32]
        users[name] = secret
        saved = save_telemt_users(users)
    if not saved:
        await update.message.reply_text("❌ Не удалось сохранить /etc/telemt/config.toml")
        return
    await refresh_telemt_after_user_change()
    link = await get_proxy_link_for_secret(secret)
    await update.message.reply_text(
        f"✅ <b>Ключ создан</b>\n\n"
        f"Пользователь: <code>{html.escape(name)}</code>\n"
        f"Secret: <code>{secret}</code>\n\n"
        f"<code>{html.escape(link or '')}</code>",
        reply_markup=_users_keyboard(load_user_records(), user_id),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ============================================================================
# RESTART & LOGS
# ============================================================================


async def cb_menu_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart service."""
    query = update.callback_query
    await query.answer()

    text = "⏳ Restarting telemt service..."
    await safe_edit_message(query,text)

    code, _, stderr = await sh("systemctl", "restart", TELEMT_SERVICE)
    if code == 0:
        text = "✅ Service restarted successfully"
    else:
        text = f"❌ Failed to restart:\n<code>{html.escape(stderr[:500])}</code>"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,
        text, reply_markup=keyboard, parse_mode="HTML"
    )


async def cb_menu_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent logs."""
    query = update.callback_query
    await query.answer()

    code, stdout, _ = await sh(
        "journalctl", "-u", TELEMT_SERVICE, "-n", "30", "--no-pager"
    )

    if code == 0:
        log_text = stdout[-1000:] if len(stdout) > 1000 else stdout
        text = f"<b>📋 Recent Logs</b>\n\n<pre>{html.escape(log_text)}</pre>"
    else:
        text = "❌ Failed to retrieve logs"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
# BACKUP & RESTORE
# ============================================================================

def list_backup_names(limit: int = 10) -> List[str]:
    try:
        if not os.path.exists(BACKUP_DIR):
            return []
        names = [
            f for f in os.listdir(BACKUP_DIR)
            if f.endswith((".tar.gz", ".tar.gz.enc")) and not f.endswith(".sha256")
        ]
        return sorted(names, reverse=True)[:limit]
    except Exception:
        return []


def safe_backup_path(name: str) -> Optional[str]:
    raw = os.path.basename(str(name or "").strip())
    if raw != name or not raw.endswith((".tar.gz", ".tar.gz.enc")) or raw.endswith(".sha256"):
        return None
    path = os.path.abspath(os.path.join(BACKUP_DIR, raw))
    base = os.path.abspath(BACKUP_DIR)
    if os.path.dirname(path) != base or not os.path.exists(path):
        return None
    return path


def backup_schedule_state() -> Dict[str, Any]:
    raw = load_json(BACKUP_SCHEDULE_FILE) or {}
    if not isinstance(raw, dict):
        raw = {}
    frequency = str(raw.get("frequency") or "off")
    if frequency not in {"off", "daily", "weekly", "monthly"}:
        frequency = "off"
    return {
        "frequency": frequency,
        "calendar": raw.get("calendar") or "",
        "updated_at": raw.get("updated_at") or "",
    }


async def run_full_backup() -> Tuple[bool, str]:
    script = (
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/i18n.sh; "
        "source /opt/pcatelegram_web/lib/telemt.sh; "
        "source /opt/pcatelegram_web/lib/website.sh; "
        "source /opt/pcatelegram_web/lib/backup.sh; "
        "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
        "create_backup \"\"; "
        "cleanup_old_backups 30"
    )
    code, stdout, stderr = await sh("bash", "-lc", script, timeout=240)
    message = (stdout.strip().splitlines()[-1:] or stderr.strip().splitlines()[-1:] or [""])[0]
    return code == 0, message


async def set_full_backup_schedule(frequency: str) -> Tuple[bool, str]:
    if frequency not in {"off", "daily", "weekly", "monthly"}:
        return False, "unsupported schedule"
    script = (
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/i18n.sh; "
        "source /opt/pcatelegram_web/lib/backup.sh; "
        "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
        f"set_backup_schedule {shlex.quote(frequency)}"
    )
    code, stdout, stderr = await sh("bash", "-lc", script, timeout=120)
    message = (stdout.strip().splitlines()[-1:] or stderr.strip().splitlines()[-1:] or [""])[0]
    return code == 0, message


async def launch_full_restore(backup_path: str) -> None:
    quoted_path = shlex.quote(backup_path)
    script = (
        "sleep 1; "
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/i18n.sh; "
        "source /opt/pcatelegram_web/lib/telemt.sh; "
        "source /opt/pcatelegram_web/lib/website.sh; "
        "source /opt/pcatelegram_web/lib/backup.sh; "
        "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
        "create_backup \"\" >/dev/null 2>&1 || true; "
        f"restore_backup {quoted_path} \"\" yes; "
        "cleanup_old_backups 30"
    )
    await asyncio.create_subprocess_exec(
        "bash",
        "-lc",
        script,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


async def cb_menu_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Backup menu."""
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    backups = list_backup_names()
    schedule = backup_schedule_state()
    labels = {
        "off": "выключено" if get_user_lang(user_id) == "ru" else "off",
        "daily": "каждый день" if get_user_lang(user_id) == "ru" else "daily",
        "weekly": "каждую неделю" if get_user_lang(user_id) == "ru" else "weekly",
        "monthly": "каждый месяц" if get_user_lang(user_id) == "ru" else "monthly",
    }

    buttons = [
        [InlineKeyboardButton("💾 Создать сейчас" if get_user_lang(user_id) == "ru" else "💾 Create now", callback_data="backup_create")],
        [
            InlineKeyboardButton("◯ Выкл" if get_user_lang(user_id) == "ru" else "◯ Off", callback_data="backup_schedule_off"),
            InlineKeyboardButton("☀ День" if get_user_lang(user_id) == "ru" else "☀ Daily", callback_data="backup_schedule_daily"),
        ],
        [
            InlineKeyboardButton("◷ Неделя" if get_user_lang(user_id) == "ru" else "◷ Weekly", callback_data="backup_schedule_weekly"),
            InlineKeyboardButton("◴ Месяц" if get_user_lang(user_id) == "ru" else "◴ Monthly", callback_data="backup_schedule_monthly"),
        ],
    ]

    if backups:
        buttons.append([InlineKeyboardButton("📋 Список" if get_user_lang(user_id) == "ru" else "📋 List", callback_data="backup_list")])
        buttons.append([InlineKeyboardButton("↩️ Восстановить" if get_user_lang(user_id) == "ru" else "↩️ Restore", callback_data="menu_restore")])

    buttons.append([InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")])

    if get_user_lang(user_id) == "ru":
        text = (
            "<b>💾 Бекапы</b>\n\n"
            f"Файлов: <code>{len(backups)}</code>\n"
            f"Расписание: <b>{labels.get(schedule['frequency'], schedule['frequency'])}</b>\n\n"
            "В бекап входит: telemt config, настройки PCAtelegram_web, ключи, отключённые ключи, сайт, шаблоны, SSL, бот, админка и история трафика."
        )
    else:
        text = (
            "<b>💾 Backups</b>\n\n"
            f"Files: <code>{len(backups)}</code>\n"
            f"Schedule: <b>{labels.get(schedule['frequency'], schedule['frequency'])}</b>\n\n"
            "Backups include telemt config, PCAtelegram_web settings, keys, disabled keys, site, templates, SSL, bot, admin panel and traffic history."
        )
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_backup_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create backup."""
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)

    await safe_edit_message(query, "⏳ Создаю полный бекап..." if get_user_lang(user_id) == "ru" else "⏳ Creating full backup...")

    ok, message = await run_full_backup()
    if ok:
        text = f"✅ Бекап создан:\n<code>{html.escape(message)}</code>" if get_user_lang(user_id) == "ru" else f"✅ Backup created:\n<code>{html.escape(message)}</code>"
    else:
        text = f"❌ Ошибка бекапа:\n<code>{html.escape(message[:500])}</code>" if get_user_lang(user_id) == "ru" else f"❌ Backup failed:\n<code>{html.escape(message[:500])}</code>"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_backup")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_backup_schedule_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    frequency = query.data.removeprefix("backup_schedule_")
    await safe_edit_message(query, "⏳ Сохраняю расписание..." if get_user_lang(user_id) == "ru" else "⏳ Saving schedule...")
    ok, message = await set_full_backup_schedule(frequency)
    if ok:
        text = "✅ Расписание обновлено." if get_user_lang(user_id) == "ru" else "✅ Backup schedule updated."
    else:
        text = f"❌ {html.escape(message[:500])}"
    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_backup")]]),
        parse_mode="HTML",
    )


async def cb_backup_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List backups."""
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)

    backups = list_backup_names()

    if not backups:
        text = "Бекапов нет" if get_user_lang(user_id) == "ru" else "No backups found"
    else:
        text = "<b>📋 Доступные бекапы</b>\n\n" if get_user_lang(user_id) == "ru" else "<b>📋 Available Backups</b>\n\n"
        for backup in backups[:10]:
            path = os.path.join(BACKUP_DIR, backup)
            size = os.path.getsize(path) / (1024 * 1024)
            text += f"<code>{html.escape(backup)}</code> ({size:.2f} MB)\n"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_backup")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_menu_restore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restore menu."""
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)

    backups = list_backup_names()

    if not backups:
        text = "❌ Нет доступных бекапов" if get_user_lang(user_id) == "ru" else "❌ No backups available"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")]]
        )
    else:
        text = "Выберите бекап для восстановления:" if get_user_lang(user_id) == "ru" else "Select backup to restore:"
        buttons = []
        for i, backup in enumerate(backups[:10]):
            buttons.append(
                [
                    InlineKeyboardButton(
                        backup, callback_data=f"restore_idx_{i}"
                    )
                ]
            )
        buttons.append([InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")])
        keyboard = InlineKeyboardMarkup(buttons)
        # Store backup list in user_data for retrieval
        context.user_data["backup_list"] = backups[:10]

    await safe_edit_message(query,text, reply_markup=keyboard)


async def cb_restore_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm or execute backup restoration."""
    query = update.callback_query
    data = query.data
    user_id = _uid(update)

    try:
        if data.startswith("restore_yes_"):
            idx = int(data.removeprefix("restore_yes_"))
        else:
            idx = int(data.removeprefix("restore_idx_"))
    except ValueError:
        await query.answer("Invalid backup selection")
        return

    backup_list = context.user_data.get("backup_list", [])
    if idx < 0 or idx >= len(backup_list):
        await query.answer("Backup not found")
        return

    backup_name = backup_list[idx]
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    await query.answer()
    if data.startswith("restore_idx_"):
        text = (
            f"Восстановить <code>{html.escape(backup_name)}</code>?\n\n"
            "Перед восстановлением будет создан свежий safety-бекап."
        ) if get_user_lang(user_id) == "ru" else (
            f"Restore <code>{html.escape(backup_name)}</code>?\n\n"
            "A fresh safety backup will be created before restoring."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Восстановить" if get_user_lang(user_id) == "ru" else "✅ Restore", callback_data=f"restore_yes_{idx}")],
            [InlineKeyboardButton(_t(user_id, "btn_cancel"), callback_data="menu_restore")],
        ])
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")
        return

    await safe_edit_message(query, f"⏳ Восстановление запущено: {html.escape(backup_name)}..." if get_user_lang(user_id) == "ru" else f"⏳ Restore started: {html.escape(backup_name)}...")

    safe_path = safe_backup_path(backup_name)
    if not safe_path:
        text = "❌ Файл бекапа не найден" if get_user_lang(user_id) == "ru" else "❌ Backup file not found"
    elif safe_path.endswith(".enc"):
        text = "❌ Зашифрованный бекап пока восстанавливается через CLI: pcatelegram_web → Восстановить." if get_user_lang(user_id) == "ru" else "❌ Encrypted backups are restored from CLI for now: pcatelegram_web → Restore."
    else:
        await launch_full_restore(safe_path)
        text = (
            f"✅ Восстановление <code>{html.escape(backup_name)}</code> запущено в фоне.\n"
            "Сервисы могут перезапуститься, через минуту откройте статус."
        ) if get_user_lang(user_id) == "ru" else (
            f"✅ Restore for <code>{html.escape(backup_name)}</code> started in background.\n"
            "Services may restart; check status in about a minute."
        )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
# UPDATE & MODE/TEMPLATE CHANGE
# ============================================================================


async def cb_menu_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update telemt by re-running the install script's update logic."""
    query = update.callback_query
    await query.answer()

    await safe_edit_message(query,"⏳ Checking for telemt updates...")

    current = await get_telemt_version()

    # Check latest release from GitHub
    code, stdout, stderr = await sh(
        "curl", "-s", "--max-time", "10",
        "https://api.github.com/repos/telemt/telemt/releases/latest",
    )

    if code != 0 or not stdout.strip():
        text = "❌ Failed to check for updates"
    else:
        try:
            release = json.loads(stdout)
            latest = release.get("tag_name", "unknown")
            if latest.lstrip("v") == current.lstrip("v"):
                text = f"✅ telemt is already up to date ({html.escape(current)})"
            else:
                text = (
                    f"ℹ️ Update available: {html.escape(current)} → {html.escape(latest)}\n\n"
                    f"Run the CLI installer to update:\n"
                    f"<code>sudo bash install.sh</code> → menu item 10"
                )
        except json.JSONDecodeError:
            text = "❌ Failed to parse release info"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_menu_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change mode or template."""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton("⚡ Switch to Lite Mode", callback_data="change_lite")],
        [InlineKeyboardButton("🛡 Switch to Pro Mode", callback_data="change_pro")],
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,
        "Change mode or template:", reply_markup=keyboard
    )


async def cb_change_lite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to lite mode — show domain selection."""
    query = update.callback_query
    await query.answer()
    # Reuse the lite mode domain selection flow
    await cb_install_mode_lite(update, context)


async def cb_change_pro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Switch to pro mode — show template categories."""
    query = update.callback_query
    await query.answer()
    # Reuse the pro mode template selection flow
    await cb_install_mode_pro(update, context)


async def cb_install_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Migrate from v1 (mtg Docker) to v2 (telemt)."""
    query = update.callback_query
    await query.answer()

    await safe_edit_message(query,"⏳ Migrating from v1...")

    # Stop old mtg container
    code, _, stderr = await sh("docker", "stop", "mtproto-proxy", timeout=30)
    if code != 0:
        code, _, stderr = await sh("docker", "stop", "mtg", timeout=30)

    # Remove old container
    await sh("docker", "rm", "mtproto-proxy", timeout=15)
    await sh("docker", "rm", "mtg", timeout=15)

    text = (
        "✅ <b>v1 container stopped and removed</b>\n\n"
        "Now select installation mode for v2:"
    )
    keyboard = get_install_mode_menu(_uid(update))
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
# WEBSITE & SSL
# ============================================================================


async def cb_menu_website(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Website and SSL management."""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton("🔄 Renew SSL Certificate", callback_data="ssl_renew")],
        [InlineKeyboardButton("📊 SSL Status", callback_data="ssl_status")],
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,
        "Website & SSL Management:", reply_markup=keyboard
    )


async def cb_ssl_renew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renew SSL certificate."""
    query = update.callback_query
    await query.answer()

    await safe_edit_message(query,"⏳ Renewing SSL certificate...")

    code, stdout, stderr = await sh("certbot", "renew", timeout=120)

    if code == 0:
        text = "✅ SSL certificate renewed successfully"
    else:
        text = f"❌ Renewal failed:\n<code>{html.escape(stderr[:500])}</code>"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back", callback_data="menu_website")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_ssl_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show SSL status."""
    query = update.callback_query
    await query.answer()

    code, stdout, _ = await sh("certbot", "certificates")

    if code == 0:
        text = f"<b>📊 SSL Certificates</b>\n\n<pre>{html.escape(stdout[:1000])}</pre>"
    else:
        text = "❌ Failed to get SSL status"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« Back", callback_data="menu_website")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def admin_web_host_hint() -> str:
    config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
    domain = str(config.get("domain") or "")
    if domain:
        return domain
    code, stdout, _ = await sh("curl", "-s", "-4", "--max-time", "5", "https://api.ipify.org", timeout=7)
    return stdout.strip() if code == 0 and stdout.strip() else "SERVER_IP"


async def cb_menu_admin_web(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = _uid(update)
    running = await check_service_status(ADMIN_WEB_SERVICE)
    host = await admin_web_host_hint()
    local_url = f"http://127.0.0.1:{ADMIN_WEB_PORT}/"
    ssh_cmd = f"ssh -L {ADMIN_WEB_PORT}:127.0.0.1:{ADMIN_WEB_PORT} root@{host}"

    if get_user_lang(user_id) == "ru":
        status = "запущена" if running else "не запущена"
        text = (
            f"<b>🖥 Web Admin</b>\n\n"
            f"Статус: <code>{status}</code>\n\n"
            "<b>Termius</b>\n"
            "1. Откройте сервер → Port Forwarding.\n"
            f"2. Добавьте Local tunnel: <code>127.0.0.1:{ADMIN_WEB_PORT}</code> → "
            f"<code>127.0.0.1:{ADMIN_WEB_PORT}</code>.\n"
            "3. Запустите tunnel и откройте в браузере:\n"
            f"<code>{html.escape(local_url)}</code>\n\n"
            "<b>Обычный SSH</b>\n"
            f"<code>{html.escape(ssh_cmd)}</code>\n\n"
            "Админка слушает только localhost на сервере и не публикуется наружу."
        )
    else:
        status = "running" if running else "not running"
        text = (
            f"<b>🖥 Web Admin</b>\n\n"
            f"Status: <code>{status}</code>\n\n"
            "<b>Termius</b>\n"
            "1. Open the server → Port Forwarding.\n"
            f"2. Add a Local tunnel: <code>127.0.0.1:{ADMIN_WEB_PORT}</code> → "
            f"<code>127.0.0.1:{ADMIN_WEB_PORT}</code>.\n"
            "3. Start the tunnel and open:\n"
            f"<code>{html.escape(local_url)}</code>\n\n"
            "<b>Regular SSH</b>\n"
            f"<code>{html.escape(ssh_cmd)}</code>\n\n"
            "The admin listens only on server localhost and is not exposed publicly."
        )

    await safe_edit_message(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")]]),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ============================================================================
# ADMIN MANAGEMENT
# ============================================================================


async def cb_menu_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список админов и кнопки управления."""
    query = update.callback_query
    await query.answer()

    if ALLOWED_IDS:
        ids_list = "\n".join(f"  • <code>{uid}</code>" for uid in sorted(ALLOWED_IDS))
        text = f"<b>👤 Администраторы</b>\n\n{ids_list}\n"
    else:
        text = "<b>👤 Администраторы</b>\n\n<i>Список пуст — доступ для всех</i>\n"

    text += (
        f"\nВсего: {len(ALLOWED_IDS)}\n\n"
        "Чтобы <b>добавить</b> — перешлите любое сообщение от нового админа, "
        "или отправьте команду:\n"
        "<code>/addadmin 123456789</code>\n\n"
        "Чтобы <b>удалить</b>:\n"
        "<code>/deladmin 123456789</code>"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ])
    await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/addadmin ID [ID2 ID3 ...] — добавить админа вручную."""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text(
            f"⛔ Доступ запрещён.\nВаш ID: <code>{update.effective_user.id}</code>",
            parse_mode="HTML",
        )
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Использование: <code>/addadmin ID [ID2 ID3 ...]</code>\n"
            "Пример: <code>/addadmin 123456789 987654321</code>",
            parse_mode="HTML",
        )
        return

    added = []
    errors = []
    for a in args:
        a = a.strip().replace(",", "")
        if not a:
            continue
        try:
            uid = int(a)
            add_admin(uid)
            added.append(str(uid))
        except ValueError:
            errors.append(a)

    parts = []
    if added:
        parts.append(f"✅ Добавлены: {', '.join(added)}")
    if errors:
        parts.append(f"❌ Ошибки: {', '.join(errors)}")

    await update.message.reply_text("\n".join(parts), parse_mode="HTML")


async def cmd_deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/deladmin ID — удалить админа."""
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text(
            f"⛔ Доступ запрещён.\nВаш ID: <code>{update.effective_user.id}</code>",
            parse_mode="HTML",
        )
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Использование: <code>/deladmin ID</code>",
            parse_mode="HTML",
        )
        return

    removed = []
    for a in args:
        a = a.strip().replace(",", "")
        try:
            uid = int(a)
            if uid == update.effective_user.id:
                await update.message.reply_text("⚠️ Нельзя удалить себя!")
                continue
            if uid in ALLOWED_IDS:
                remove_admin(uid)
                removed.append(str(uid))
            else:
                await update.message.reply_text(f"ID {uid} не найден в списке")
        except ValueError:
            await update.message.reply_text(f"❌ Некорректный ID: {html.escape(a)}")

    if removed:
        await update.message.reply_text(f"✅ Удалены: {', '.join(removed)}")


async def cb_menu_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Credits and acknowledgements."""
    query = update.callback_query
    await query.answer()

    text = (
        f"<b>ℹ️ Credits & Acknowledgements</b>\n\n"
        f"<b>PCAtelegram_web v{PCATELEGRAM_WEB_VERSION}</b>\n\n"
        f"Built with love for the Telegram community\n\n"
        f"<b>Special thanks to:</b>\n\n"
        f"🙏 <b>telemt</b> - MTProxy engine\n"
        f"   High-performance proxy core\n\n"
        f"🎨 <b>HTML5UP</b> - Beautiful web templates\n"
        f"   Responsive design & themes\n\n"
        f"📚 <b>Learning Zone</b> - Educational resources\n"
        f"   Community learning support\n\n"
        f"🚀 <b>Start Bootstrap</b> - Bootstrap templates\n"
        f"   Professional design framework\n\n"
        f"💬 <b>Community</b> - Your feedback & support\n\n"
        f"<i>PCAtelegram_web is open-source and community-driven</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
# REMOVE
# ============================================================================


async def cb_menu_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove installation."""
    query = update.callback_query
    await query.answer()

    text = (
        "<b>⚠️ Remove PCAtelegram_web</b>\n\n"
        "This will completely remove the installation.\n"
        "Are you sure?"
    )

    buttons = [
        [InlineKeyboardButton("❌ Yes, Remove", callback_data="remove_confirm")],
        [InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


async def cb_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm removal."""
    query = update.callback_query
    await query.answer()

    await safe_edit_message(query,"⏳ Removing PCAtelegram_web...")

    # Stop service
    await sh("systemctl", "stop", TELEMT_SERVICE)

    # Remove directories
    for path in ["/opt/pcatelegram_web", WEBSITE_ROOT]:
        await sh("rm", "-rf", path)

    text = "✅ PCAtelegram_web removed successfully"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(_t(_uid(update), "btn_back"), callback_data="menu_main")]]
    )
    await safe_edit_message(query,text, reply_markup=keyboard, parse_mode="HTML")


# ============================================================================
# CALLBACK ROUTING
# ============================================================================


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route all callbacks."""
    query = update.callback_query
    data = query.data

    # ── Авто-регистрация админа (до проверки доступа!) ──
    if data.startswith("admin_confirm_"):
        await query.answer()
        try:
            new_admin_id = int(data.split("_")[-1])
        except (ValueError, IndexError):
            await safe_edit_message(query, "❌ Ошибка: некорректный ID")
            return
        # Безопасность: только тот кто нажал кнопку может стать админом
        if update.effective_user.id != new_admin_id:
            await query.answer("Эта кнопка не для вас", show_alert=True)
            return
        # Race condition: если кто-то уже стал админом
        if not _WAITING_FOR_ADMIN:
            await safe_edit_message(query, "ℹ️ Администратор уже назначен.")
            return
        add_admin(new_admin_id)
        await safe_edit_message(
            query,
            f"✅ <b>Вы назначены администратором!</b>\n\n"
            f"ID: <code>{new_admin_id}</code>\n\n"
            f"Нажмите /start чтобы открыть меню.",
            parse_mode="HTML",
        )
        return

    if data == "admin_cancel":
        await query.answer()
        await safe_edit_message(
            query,
            "👋 Ок. Напишите /start когда будете готовы.",
        )
        return

    # Access control
    if not is_user_allowed(update.effective_user.id):
        await query.answer("Доступ запрещён")
        return

    user_id = update.effective_user.id

    # Main menu
    if data == "menu_main":
        await query.answer()
        buttons = get_main_menu(user_id)
        text = (
            f"<b>{_tf(user_id, 'welcome_title', PCATELEGRAM_WEB_VERSION)}</b>\n\n"
            f"{_t(user_id, 'welcome_subtitle')}\n"
            f"{_t(user_id, 'welcome_prompt')}"
        )
        await safe_edit_message(query, text, reply_markup=buttons, parse_mode="HTML")
        return

    if data == "close_menu":
        await query.answer()
        await query.delete_message()
        return

    # Language picker
    if data == "menu_lang":
        await query.answer()
        current = get_user_lang(user_id)
        title = _t(user_id, "lang_title")
        curr_line = _tf(user_id, "lang_current", get_language_name(current))
        prompt = _t(user_id, "lang_choose")
        text = f"<b>{title}</b>\n\n{curr_line}\n\n{prompt}"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_set_en"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_set_ru"),
            ],
            [InlineKeyboardButton(_t(user_id, "btn_back"), callback_data="menu_main")],
        ])
        await safe_edit_message(query, text, reply_markup=keyboard, parse_mode="HTML")
        return

    if data.startswith("lang_set_"):
        code = data.replace("lang_set_", "", 1)
        if code in SUPPORTED_LANGS:
            set_user_lang(user_id, code)
            await query.answer(_tf(user_id, "lang_saved", get_language_name(code)))
            # Re-render main menu in the new language
            buttons = get_main_menu(user_id)
            text = (
                f"<b>{_tf(user_id, 'welcome_title', PCATELEGRAM_WEB_VERSION)}</b>\n\n"
                f"{_t(user_id, 'welcome_subtitle')}\n"
                f"{_t(user_id, 'welcome_prompt')}"
            )
            await safe_edit_message(query, text, reply_markup=buttons, parse_mode="HTML")
        else:
            await query.answer("Unsupported language")
        return

    # Dispatch to handlers
    handlers = {
        "menu_install": cb_menu_install,
        "menu_status": cb_menu_status,
        "menu_link": cb_menu_link,
        "menu_share": cb_menu_share,
        "menu_restart": cb_menu_restart,
        "menu_logs": cb_menu_logs,
        "menu_backup": cb_menu_backup,
        "menu_restore": cb_menu_restore,
        "menu_update": cb_menu_update,
        "menu_change": cb_menu_change,
        "menu_website": cb_menu_website,
        "menu_credits": cb_menu_credits,
        "menu_admin_web": cb_menu_admin_web,
        "menu_admins": cb_menu_admins,
        "menu_users": cb_menu_users,
        "menu_remove": cb_menu_remove,
        "install_mode_lite": cb_install_mode_lite,
        "install_mode_pro": cb_install_mode_pro,
        "backup_create": cb_backup_create,
        "backup_list": cb_backup_list,
        "ssl_renew": cb_ssl_renew,
        "ssl_status": cb_ssl_status,
        "remove_confirm": cb_remove_confirm,
        "change_lite": cb_change_lite,
        "change_pro": cb_change_pro,
        "install_migrate": cb_install_migrate,
        "menu_stats": cb_menu_stats,
        "backup_schedule_off": cb_backup_schedule_set,
        "backup_schedule_daily": cb_backup_schedule_set,
        "backup_schedule_weekly": cb_backup_schedule_set,
        "backup_schedule_monthly": cb_backup_schedule_set,
    }

    # Custom git template URL prompt
    if data == "pro_custom_git":
        await query.answer()
        _CUSTOM_GIT_WAITERS[user_id] = True
        title = _t(user_id, "cg_title")
        body = _t(user_id, "cg_ask_url")
        await safe_edit_message(
            query,
            f"<b>{title}</b>\n\n{body}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(_t(user_id, "btn_cancel"), callback_data="menu_main")]]
            ),
            parse_mode="HTML",
        )
        return

    # Pattern-based handlers
    if data.startswith("lite_dom_"):
        await cb_lite_domain(update, context)
    elif data == "user_add":
        await cb_user_add(update, context)
    elif data.startswith("user_view_"):
        await cb_user_view(update, context)
    elif data.startswith("user_qr_"):
        await cb_user_qr(update, context)
    elif data.startswith("user_ip_limit_"):
        await cb_user_ip_limit(update, context)
    elif data.startswith("user_toggle_"):
        await cb_user_toggle(update, context)
    elif data.startswith("user_del_yes_"):
        await cb_user_delete_confirm(update, context)
    elif data.startswith("user_del_"):
        await cb_user_delete(update, context)
    elif data.startswith("pro_cat_"):
        await cb_pro_category(update, context)
    elif data.startswith("pro_tpl_"):
        await cb_pro_template(update, context)
    elif data.startswith("pro_confirm_"):
        await cb_pro_confirm(update, context)
    elif data.startswith("restore_idx_") or data.startswith("restore_yes_"):
        await cb_restore_backup(update, context)
    elif data in handlers:
        await handlers[data](update, context)
    else:
        await query.answer("Unknown action")


# ============================================================================
# ERROR HANDLERS
# ============================================================================


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text input. Currently used for custom git template URLs."""
    if update.message is None or update.message.text is None:
        return
    if not is_user_allowed(update.effective_user.id):
        return
    user_id = update.effective_user.id
    ip_limit_user = context.user_data.pop("awaiting_user_ip_limit", None)
    if ip_limit_user:
        await set_user_ip_limit_from_text(update, context, update.message.text.strip(), str(ip_limit_user))
        return
    if context.user_data.pop("awaiting_user_name", False):
        await create_user_from_text(update, context, update.message.text.strip())
        return

    # Only act when we're explicitly waiting for a custom-git URL
    if not _CUSTOM_GIT_WAITERS.pop(user_id, False):
        return
    url = update.message.text.strip()
    if not _validate_custom_git_url(url):
        await update.message.reply_text(_t(user_id, "cg_invalid"), parse_mode="HTML")
        return
    await update.message.reply_text(_tf(user_id, "cg_cloning", html.escape(url)), parse_mode="HTML")
    ok, tpl_id, info = await _download_custom_git_template(url)
    if not ok:
        await update.message.reply_text(_t(user_id, info), parse_mode="HTML")
        return
    # Success — record in PCAtelegram_web config. Use "template_id" (canonical
    # field name written by install.sh/save_pcatelegram_web_config).
    config = load_json(PCATELEGRAM_WEB_CONFIG) or {}
    config["template_id"] = tpl_id
    config["template_source"] = url
    save_json(PCATELEGRAM_WEB_CONFIG, config)
    if config.get("mode") == "pro" and os.path.isdir(info):
        try:
            os.makedirs(WEBSITE_ROOT, exist_ok=True)
            for entry in os.listdir(WEBSITE_ROOT):
                path = os.path.join(WEBSITE_ROOT, entry)
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            for entry in os.listdir(info):
                src = os.path.join(info, entry)
                dst = os.path.join(WEBSITE_ROOT, entry)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        except OSError as e:
            logger.error("custom template deploy failed: %s", e)
    await update.message.reply_text(
        _tf(user_id, "cg_ok_fmt", html.escape(tpl_id)),
        reply_markup=get_main_menu(user_id),
        parse_mode="HTML",
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.error(f"Exception while handling an update:", exc_info=context.error)


# ============================================================================
# MAIN APPLICATION
# ============================================================================


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in .env file")
        return

    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("logs", cmd_logs))
    application.add_handler(CommandHandler("lang", cmd_lang))
    application.add_handler(CommandHandler("addadmin", cmd_addadmin))
    application.add_handler(CommandHandler("deladmin", cmd_deladmin))

    # Callback query handler (buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Text message handler (for custom git URL input)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text_message
    ))

    # Error handler
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info(f"PCAtelegram_web v{PCATELEGRAM_WEB_VERSION} bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
