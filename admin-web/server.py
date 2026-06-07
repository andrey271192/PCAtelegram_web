#!/usr/bin/env python3
"""
PCAtelegram_web local web admin.

The service is publicly reachable by default and protected with Basic Auth.
Installers generate /root/pcatelegram_web-admin.password for credentials.
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ADMIN_DIR = Path(os.getenv("PCATELEGRAM_WEB_ADMIN_DIR", "/opt/pcatelegram_web-admin"))
STATIC_DIR = Path(os.getenv("PCATELEGRAM_WEB_ADMIN_STATIC", str(ADMIN_DIR / "static")))

PCATELEGRAM_WEB_CONFIG = Path(os.getenv("PCATELEGRAM_WEB_CONFIG", "/opt/pcatelegram_web/config.json"))
TELEMT_CONFIG = Path(os.getenv("TELEMT_CONFIG", "/etc/telemt/config.toml"))
HISTORY_FILE = Path(os.getenv("PCATELEGRAM_WEB_STATS_HISTORY", "/opt/pcatelegram_web/stats_history.csv"))
USER_HISTORY_FILE = Path(os.getenv("PCATELEGRAM_WEB_USER_STATS_HISTORY", "/opt/pcatelegram_web/user_stats_history.csv"))
CURRENT_STATS = Path(os.getenv("PCATELEGRAM_WEB_STATS_CURRENT", "/run/pcatelegram_web/stats_current.json"))
BACKUP_DIR = Path(os.getenv("PCATELEGRAM_WEB_BACKUP_DIR", "/opt/pcatelegram_web/backups"))
INSTALL_DIR = Path(os.getenv("PCATELEGRAM_WEB_DIR", "/opt/pcatelegram_web"))
BOT_DIR = Path(os.getenv("PCATELEGRAM_WEB_BOT_DIR", "/opt/pcatelegram_web-bot"))
DISABLED_USERS_FILE = Path(os.getenv("PCATELEGRAM_WEB_DISABLED_USERS", "/opt/pcatelegram_web/disabled_users.json"))
USER_LOCK_FILE = Path(os.getenv("PCATELEGRAM_WEB_USER_LOCK", "/run/pcatelegram_web/admin-users.lock"))
SHARED_443_CONFIG = Path(os.getenv("PCATELEGRAM_WEB_SHARED_443", "/opt/pcatelegram_web/shared-443.json"))
BACKUP_SCHEDULE_FILE = Path(os.getenv("PCATELEGRAM_WEB_BACKUP_SCHEDULE", "/opt/pcatelegram_web/backup_schedule.json"))
BACKUP_RESTORE_LOG = Path(os.getenv("PCATELEGRAM_WEB_BACKUP_RESTORE_LOG", "/var/log/pcatelegram_web-restore.log"))
WARP_CONFIG_FILE = Path(os.getenv("PCATELEGRAM_WEB_WARP_CONFIG", "/opt/pcatelegram_web/warp.json"))
MIERU_CONFIG_FILE = Path(os.getenv("PCATELEGRAM_WEB_MIERU_CONFIG", "/opt/pcatelegram_web/mieru.json"))
MIERU_SERVER_CONFIG_FILE = Path(os.getenv("PCATELEGRAM_WEB_MIERU_SERVER_CONFIG", "/opt/pcatelegram_web/mieru_server_config.json"))
WEBSITE_ROOT = Path(os.getenv("PCATELEGRAM_WEB_SITE_ROOT", "/var/www/pcatelegram_web-site"))
NGINX_MASK_CONF = Path(os.getenv("PCATELEGRAM_WEB_NGINX_MASK_CONF", "/etc/nginx/sites-available/pcatelegram_web-mask"))
NGINX_MASK_LINK = Path(os.getenv("PCATELEGRAM_WEB_NGINX_MASK_LINK", "/etc/nginx/sites-enabled/pcatelegram_web-mask"))

HOST = os.getenv("PCATELEGRAM_WEB_ADMIN_HOST", "0.0.0.0")
PORT = int(os.getenv("PCATELEGRAM_WEB_ADMIN_PORT", "1984"))
ADMIN_USER = os.getenv("PCATELEGRAM_WEB_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("PCATELEGRAM_WEB_ADMIN_PASSWORD", "")
ADMIN_AUTH_FILE = Path(os.getenv("PCATELEGRAM_WEB_ADMIN_AUTH_FILE", "/root/pcatelegram_web-admin.password"))
SESSION_COOKIE = "pcatelegram_web_session"
SESSION_TTL_SECONDS = 12 * 60 * 60
SESSIONS: dict[str, float] = {}
VERSION = "2.5.0"
USER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")
LANG_RE = re.compile(r"^(en|ru)$")
HOST_RE = re.compile(r"^(?=.{1,253}$)([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")
SENSITIVE_CONFIG_KEYS = {"secret"}
BACKUP_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+\.tar\.gz(\.enc)?$")
MAX_UNIQUE_IP_LIMIT = 1000000
TELEMT_RESTART_DEBOUNCE_SECONDS = float(os.getenv("PCATELEGRAM_WEB_TELEMT_RESTART_DEBOUNCE", "8"))
_LAST_TELEMT_RESTART = 0.0
TRAFFIC_WINDOWS = {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "24h": 24 * 60 * 60,
    "month": 30 * 24 * 60 * 60,
}


def load_admin_credentials() -> tuple[str, str]:
    if ADMIN_PASSWORD:
        return ADMIN_USER or "admin", ADMIN_PASSWORD
    user = "admin"
    password = "admin"
    try:
        for line in ADMIN_AUTH_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("user="):
                user = line.split("=", 1)[1].strip() or "admin"
            if line.startswith("password="):
                password = line.split("=", 1)[1].strip() or "admin"
    except OSError:
        pass
    return user, password


def write_admin_credentials(username: str, password: str) -> None:
    ADMIN_AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ADMIN_AUTH_FILE.with_suffix(".tmp")
    body = "\n".join([
        f"user={username}",
        f"password={password}",
        f"url=http://{public_host_for_notes()}:{PORT}/",
        "",
    ])
    tmp.write_text(body, encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(ADMIN_AUTH_FILE)


def public_host_for_notes() -> str:
    try:
        host = socket.gethostbyname(socket.gethostname())
        if host and not host.startswith("127."):
            return host
    except OSError:
        pass
    code, out, _ = run(["hostname", "-I"], timeout=3)
    if code == 0:
        first = (out.strip().split() or [""])[0]
        if first:
            return first
    return HOST if HOST != "0.0.0.0" else "127.0.0.1"


def session_secret() -> bytes:
    user, password = load_admin_credentials()
    return f"{user}:{password}:{ADMIN_AUTH_FILE}".encode("utf-8")


def make_session() -> str:
    nonce = secrets.token_urlsafe(24)
    exp = int(time.time() + SESSION_TTL_SECONDS)
    payload = f"{exp}.{nonce}"
    sig = hmac.new(session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload}.{sig}"
    SESSIONS[token] = exp
    return token


def session_is_valid(token: str) -> bool:
    if not token:
        return False
    exp = SESSIONS.get(token)
    if not exp:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        exp_raw, nonce, sig = parts
        if not exp_raw.isdigit() or not nonce:
            return False
        payload = f"{exp_raw}.{nonce}"
        expected = hmac.new(session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        exp = int(exp_raw)
    if exp < time.time():
        SESSIONS.pop(token, None)
        return False
    SESSIONS[token] = time.time() + SESSION_TTL_SECONDS
    return True


def clear_session(token: str) -> None:
    if token:
        SESSIONS.pop(token, None)


def login_page() -> bytes:
    return """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PCAtelegram_web Login</title>
  <style>
    :root {
      --bg: #efe6df;
      --card: #fffafd;
      --text: #251f1d;
      --muted: #665b55;
      --line: #d8c8bd;
      --brand: #9a5f00;
      --brand-dark: #805000;
      --soft: #ffddb8;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at 18% 16%, rgba(154, 95, 0, .10), transparent 30%),
        linear-gradient(135deg, #efe6df, #f7efe9 48%, #eaded6);
      color: var(--text);
      padding: 24px;
    }
    .login-card {
      width: min(560px, 100%);
      border: 1px solid rgba(64, 49, 43, .22);
      border-radius: 28px;
      background: color-mix(in srgb, var(--card) 96%, white);
      box-shadow: 0 30px 80px rgba(33, 28, 25, .22);
      padding: clamp(26px, 5vw, 44px);
    }
    .brand {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-bottom: 30px;
    }
    .mark {
      width: 64px;
      height: 64px;
      border-radius: 20px;
      display: grid;
      place-items: center;
      color: white;
      background: linear-gradient(135deg, #b87306, #805000);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.24), 0 14px 30px rgba(128,80,0,.24);
      font-weight: 900;
      letter-spacing: 0;
      font-size: 24px;
    }
    h1 {
      margin: 0;
      font-size: clamp(28px, 5vw, 40px);
      line-height: 1.08;
      letter-spacing: 0;
    }
    .subtitle { margin-top: 6px; color: var(--muted); font-size: 15px; }
    form { display: grid; gap: 18px; }
    label {
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-weight: 800;
      font-size: 14px;
    }
    input {
      min-height: 58px;
      border: 2px solid var(--line);
      border-radius: 16px;
      background: #fffbff;
      color: var(--text);
      font: inherit;
      font-size: 20px;
      padding: 0 18px;
      outline: none;
    }
    input:focus {
      border-color: var(--brand);
      box-shadow: 0 0 0 4px rgba(154, 95, 0, .13);
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 14px;
      margin-top: 10px;
      flex-wrap: wrap;
    }
    button {
      min-height: 56px;
      border: 0;
      border-radius: 999px;
      padding: 0 32px;
      font: inherit;
      font-size: 18px;
      font-weight: 900;
      cursor: pointer;
    }
    .soft { background: var(--soft); color: var(--text); }
    .primary { background: var(--brand); color: white; min-width: 150px; }
    .primary:hover { background: var(--brand-dark); }
    .hint { margin-top: 18px; color: var(--muted); font-size: 13px; }
    .error { min-height: 22px; color: #b42318; font-weight: 800; }
    @media (max-width: 520px) {
      body { padding: 14px; }
      .login-card { border-radius: 20px; }
      .actions button { flex: 1; }
    }
  </style>
</head>
<body>
  <main class="login-card">
    <div class="brand">
      <div class="mark">PCA</div>
      <div>
        <h1>PCAtelegram_web</h1>
        <div class="subtitle">Web admin panel</div>
      </div>
    </div>
    <form id="loginForm">
      <label>Имя пользователя
        <input name="username" autocomplete="username" value="admin" required autofocus>
      </label>
      <label>Пароль
        <input name="password" type="password" autocomplete="current-password" value="admin" required>
      </label>
      <div id="error" class="error"></div>
      <div class="actions">
        <button type="reset" class="soft">Очистить</button>
        <button type="submit" class="primary">Войти</button>
      </div>
    </form>
    <p class="hint">По умолчанию: admin / admin. Смените пароль в Settings после входа.</p>
  </main>
  <script>
    document.getElementById("loginForm").addEventListener("submit", async function (ev) {
      ev.preventDefault();
      const error = document.getElementById("error");
      error.textContent = "";
      const form = new FormData(ev.currentTarget);
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: String(form.get("username") || ""),
          password: String(form.get("password") || "")
        })
      });
      if (res.ok) {
        window.location.assign("/");
      } else {
        error.textContent = "Неверный логин или пароль";
      }
    });
  </script>
</body>
</html>
""".encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:  # pragma: no cover - system dependent
        return 125, "", str(exc)


def run_bytes(cmd: list[str], timeout: int = 8) -> tuple[int, bytes, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - system dependent
        return 125, b"", str(exc)


def run_bash_env(script: str, env_extra: dict[str, str] | None = None, timeout: int = 180) -> tuple[int, str, str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        proc = subprocess.run(
            ["bash", "-lc", script],
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:  # pragma: no cover - system dependent
        return 125, "", str(exc)


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("w", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.handle:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def load_json(path: Path, fallback: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return fallback


def save_json(path: Path, data: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    os.chmod(tmp, mode)
    tmp.replace(path)


def read_language(config: dict[str, Any] | None = None) -> str:
    config = config or load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    lang = str(config.get("language") or config.get("lang") or "").strip().lower()
    marker = INSTALL_DIR / ".language"
    if lang not in {"en", "ru"} and marker.exists():
        try:
            lang = marker.read_text(encoding="utf-8", errors="ignore").strip().lower()[:2]
        except OSError:
            lang = ""
    return lang if lang in {"en", "ru"} else "en"


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key not in SENSITIVE_CONFIG_KEYS}


def write_language(lang: str) -> dict[str, Any]:
    lang = str(lang or "").strip().lower()
    if not LANG_RE.match(lang):
        raise ValueError("unsupported language")
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    if not isinstance(config, dict):
        config = {}
    config["language"] = lang
    config["updated_at"] = utc_now()
    save_json(PCATELEGRAM_WEB_CONFIG, config)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    (INSTALL_DIR / ".language").write_text(lang + "\n", encoding="utf-8")
    bot_env = BOT_DIR / ".env"
    if bot_env.exists():
        lines = bot_env.read_text(encoding="utf-8", errors="ignore").splitlines()
        found = False
        out = []
        for line in lines:
            if line.startswith("BOT_LANG="):
                out.append(f"BOT_LANG={lang}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"BOT_LANG={lang}")
        bot_env.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        os.chmod(bot_env, 0o600)
    return {"language": lang}


def read_telemt_users() -> dict[str, str]:
    if not TELEMT_CONFIG.exists():
        return {}
    users: dict[str, str] = {}
    in_users = False
    for raw in TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line == "[access.users]":
            in_users = True
            continue
        if in_users and line.startswith("["):
            break
        if not in_users or not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = parse_toml_key(name)
        value = value.strip().split("#", 1)[0].strip()
        if value.startswith('"') and '"' in value[1:]:
            value = value[1:].split('"', 1)[0]
        elif value.startswith("'") and "'" in value[1:]:
            value = value[1:].split("'", 1)[0]
        if USER_RE.match(name) and value:
            users[name] = value
    return users


def read_toml_int_table(table: str) -> dict[str, int]:
    if not TELEMT_CONFIG.exists():
        return {}
    values: dict[str, int] = {}
    section = f"[{table}]"
    in_table = False
    for raw in TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line == section:
            in_table = True
            continue
        if in_table and line.startswith("["):
            break
        if not in_table or not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = parse_toml_key(name)
        if not USER_RE.match(name):
            continue
        raw_value = value.strip().split("#", 1)[0].strip().strip('"').strip("'")
        try:
            number = int(raw_value)
        except ValueError:
            continue
        values[name] = max(0, number)
    return values


def read_user_max_unique_ips() -> dict[str, int]:
    return read_toml_int_table("access.user_max_unique_ips")


def mask_secret(value: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    if len(clean) <= 8:
        return "••••"
    return f"{clean[:4]}••••{clean[-4:]}"


def read_warp_config() -> dict[str, Any]:
    raw = load_json(WARP_CONFIG_FILE, {}) or {}
    if not isinstance(raw, dict):
        raw = {}
    users = raw.get("users") if isinstance(raw.get("users"), dict) else {}
    clean_users: dict[str, dict[str, str]] = {}
    for name, item in users.items():
        name_s = str(name or "").strip()
        if not USER_RE.match(name_s) or not isinstance(item, dict):
            continue
        mode = str(item.get("mode") or "off").strip().lower()
        if mode not in {"off", "warp", "warp_plus"}:
            mode = "off"
        clean_users[name_s] = {
            "mode": mode,
            "license_key": str(item.get("license_key") or "").strip(),
            "updated_at": str(item.get("updated_at") or ""),
        }
    mode = str(raw.get("mode") or "off").strip().lower()
    if mode not in {"off", "warp", "warp_plus"}:
        mode = "off"
    scope = str(raw.get("scope") or "all").strip().lower()
    if scope not in {"all", "user"}:
        scope = "all"
    user = str(raw.get("user") or "").strip()
    if user and not USER_RE.match(user):
        user = ""
    return {
        "version": 1,
        "enabled": bool(raw.get("enabled")) and mode != "off",
        "mode": mode,
        "scope": scope,
        "user": user,
        "license_key": str(raw.get("license_key") or "").strip(),
        "users": clean_users,
        "updated_at": str(raw.get("updated_at") or ""),
    }


def write_warp_config(config: dict[str, Any]) -> None:
    config = dict(config)
    config["version"] = 1
    config["updated_at"] = utc_now()
    save_json(WARP_CONFIG_FILE, config, mode=0o600)


def warp_runtime_status() -> dict[str, Any]:
    warp_cli = shutil.which("warp-cli")
    payload: dict[str, Any] = {
        "installed": bool(warp_cli),
        "command": warp_cli or "",
        "status": "not_installed",
        "account": "",
        "mode": "",
        "last_error": "",
    }
    if not warp_cli:
        return payload
    code, out, err = run([warp_cli, "status"], timeout=8)
    payload["status"] = (out or err).strip()
    if code != 0:
        payload["last_error"] = err.strip() or out.strip()
    code, out, err = run([warp_cli, "registration", "show"], timeout=8)
    if code == 0:
        payload["account"] = out.strip()
    else:
        payload["account"] = ""
    code, out, _ = run([warp_cli, "mode"], timeout=8)
    if code == 0:
        payload["mode"] = out.strip()
    return payload


def public_warp_config() -> dict[str, Any]:
    cfg = read_warp_config()
    users_public: dict[str, dict[str, str]] = {}
    for name, item in cfg.get("users", {}).items():
        users_public[name] = {
            "mode": item.get("mode", "off"),
            "license_mask": mask_secret(item.get("license_key", "")),
            "updated_at": item.get("updated_at", ""),
        }
    return {
        "enabled": cfg["enabled"],
        "mode": cfg["mode"],
        "scope": cfg["scope"],
        "user": cfg["user"],
        "license_mask": mask_secret(cfg.get("license_key", "")),
        "users": users_public,
        "updated_at": cfg.get("updated_at", ""),
        "runtime": warp_runtime_status(),
        "per_user_runtime_supported": False,
        "per_user_note": "telemt has no documented per-user upstream routing; per-user WARP settings are stored as client metadata.",
    }


def user_warp_payload(name: str) -> dict[str, Any]:
    cfg = read_warp_config()
    item = cfg.get("users", {}).get(name, {})
    inherited = cfg["enabled"] and cfg["scope"] == "all"
    selected = cfg["enabled"] and cfg["scope"] == "user" and cfg.get("user") == name
    mode = "off"
    source = "none"
    if inherited:
        mode = cfg["mode"]
        source = "all"
    elif selected:
        mode = item.get("mode") or cfg["mode"]
        source = "user"
    elif item:
        mode = item.get("mode", "off")
        source = "stored"
    return {
        "mode": mode,
        "source": source,
        "enabled": mode != "off" and source in {"all", "user"},
        "license_mask": mask_secret(item.get("license_key", "") if source != "all" else cfg.get("license_key", "")),
    }


def install_warp_cli() -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": False, "installed": bool(shutil.which("warp-cli")), "commands": [], "warnings": []}
    if result["installed"]:
        return result
    if os.geteuid() != 0:
        result["warnings"].append("root required to install cloudflare-warp")
        return result

    def call(label: str, cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
        result["attempted"] = True
        code, out, err = run(cmd, timeout=timeout)
        result["commands"].append({"cmd": label, "exit_code": code})
        return code, out, err

    apt_get = shutil.which("apt-get")
    dnf = shutil.which("dnf")
    yum = shutil.which("yum")

    if apt_get:
        script = r"""
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl gpg lsb-release ca-certificates
install -d -m 0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/cloudflare-client.list
apt-get update
apt-get install -y cloudflare-warp
"""
        code, _, err = call("install cloudflare-warp via apt", ["bash", "-lc", script], timeout=420)
        if code != 0:
            result["warnings"].append(err.strip() or "apt install failed")
    elif dnf or yum:
        manager = dnf or yum
        repo_url = "https://pkg.cloudflareclient.com/cloudflare-warp-ascii.repo"
        script = f"""
set -e
rpm --import https://pkg.cloudflareclient.com/pubkey.gpg || true
curl -fsSL {shlex.quote(repo_url)} > /etc/yum.repos.d/cloudflare-warp.repo
{shlex.quote(manager)} install -y cloudflare-warp
"""
        code, _, err = call("install cloudflare-warp via rpm repo", ["bash", "-lc", script], timeout=420)
        if code != 0:
            result["warnings"].append(err.strip() or "rpm install failed")
    else:
        result["warnings"].append("supported package manager not found")

    result["installed"] = bool(shutil.which("warp-cli"))
    if not result["installed"] and not result["warnings"]:
        result["warnings"].append("warp-cli still not available after install")
    return result


def apply_warp_runtime(cfg: dict[str, Any]) -> dict[str, Any]:
    warp_cli = shutil.which("warp-cli")
    result: dict[str, Any] = {"applied": False, "install": {"attempted": False, "installed": bool(warp_cli)}, "commands": [], "warnings": []}
    if cfg["enabled"] and cfg["mode"] != "off" and not warp_cli:
        install_result = install_warp_cli()
        result["install"] = install_result
        result["warnings"].extend(install_result.get("warnings", []))
        warp_cli = shutil.which("warp-cli")
    if (not cfg["enabled"] or cfg["mode"] == "off") and not warp_cli:
        result["applied"] = True
        return result
    if not warp_cli:
        result["warnings"].append("warp-cli not installed")
        return result

    def call(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
        code, out, err = run([warp_cli, *args], timeout=timeout)
        shown_args = list(args)
        if len(shown_args) >= 3 and shown_args[0:2] == ["registration", "license"]:
            shown_args[2] = mask_secret(shown_args[2])
        result["commands"].append({"cmd": "warp-cli " + " ".join(shown_args), "exit_code": code})
        return code, out, err

    if not cfg["enabled"] or cfg["mode"] == "off":
        call(["disconnect"], timeout=15)
        result["applied"] = True
        return result

    if cfg["scope"] == "user":
        result["warnings"].append("per-user WARP route saved only; telemt per-user upstream routing is not documented")
        return result

    run(["systemctl", "enable", "--now", "warp-svc"], timeout=20)
    code, _, _ = call(["registration", "show"], timeout=10)
    if code != 0:
        call(["registration", "new"], timeout=30)
    if cfg["mode"] == "warp_plus":
        license_key = str(cfg.get("license_key") or "").strip()
        if license_key:
            call(["registration", "license", license_key], timeout=30)
        else:
            result["warnings"].append("WARP+ selected without license key")
    call(["mode", "warp+doh"], timeout=15)
    code, _, err = call(["connect"], timeout=30)
    result["applied"] = code == 0
    if code != 0 and err:
        result["warnings"].append(err.strip())
    return result


def normalize_mieru_port(value: Any) -> int:
    port = normalize_port(value)
    if port < 1025:
        raise ValueError("Mieru port must be between 1025 and 65535")
    return port


def normalize_mieru_protocol(value: Any) -> str:
    proto = str(value or "TCP").strip().upper()
    if proto not in {"TCP", "UDP"}:
        raise ValueError("Mieru protocol must be TCP or UDP")
    return proto


def read_mieru_config() -> dict[str, Any]:
    raw = load_json(MIERU_CONFIG_FILE, {}) or {}
    if not isinstance(raw, dict):
        raw = {}
    user = str(raw.get("user") or "main").strip()
    if not USER_RE.match(user):
        user = "main"
    try:
        port = normalize_mieru_port(raw.get("port") or 2999)
    except ValueError:
        port = 2999
    try:
        protocol = normalize_mieru_protocol(raw.get("protocol") or "TCP")
    except ValueError:
        protocol = "TCP"
    return {
        "version": 1,
        "enabled": bool(raw.get("enabled")),
        "port": port,
        "protocol": protocol,
        "user": user,
        "password": str(raw.get("password") or "").strip(),
        "subscription_token": str(raw.get("subscription_token") or "").strip(),
        "updated_at": str(raw.get("updated_at") or ""),
    }


def write_mieru_config(config: dict[str, Any]) -> None:
    cfg = dict(config)
    cfg["version"] = 1
    cfg["updated_at"] = utc_now()
    save_json(MIERU_CONFIG_FILE, cfg, mode=0o600)


def mieru_installed() -> bool:
    return bool(shutil.which("mita")) or service_status("mita") != "not_installed"


def mieru_status_text() -> str:
    mita = shutil.which("mita")
    if not mita:
        return "mita not installed"
    code, out, err = run([mita, "status"], timeout=8)
    text = (out or err).strip()
    return text or f"mita status exit {code}"


def mieru_port_conflicts(port: int, protocol: str) -> list[dict[str, Any]]:
    listeners, _ = collect_port_listeners(port)
    proto = protocol.upper()
    conflicts = []
    for item in listeners:
        if str(item.get("proto") or "").upper() != proto:
            continue
        process = str(item.get("process") or "").lower()
        if "mita" in process or "mieru" in process:
            continue
        conflicts.append(item)
    return conflicts


def mieru_server_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "portBindings": [
            {
                "port": int(cfg["port"]),
                "protocol": cfg["protocol"],
            }
        ],
        "users": [
            {
                "name": cfg["user"],
                "password": cfg["password"],
            }
        ],
        "loggingLevel": "INFO",
        "mtu": 1400,
    }


def mieru_client_config(cfg: dict[str, Any]) -> dict[str, Any]:
    host = public_host_for_notes()
    ip_address = host if re.match(r"^[0-9a-fA-F:.]+$", host) else ""
    domain_name = "" if ip_address else host
    return {
        "profiles": [
            {
                "profileName": "PCAtelegram_web",
                "user": {
                    "name": cfg["user"],
                    "password": cfg["password"],
                },
                "servers": [
                    {
                        "ipAddress": ip_address,
                        "domainName": domain_name,
                        "portBindings": [
                            {
                                "port": int(cfg["port"]),
                                "protocol": cfg["protocol"],
                            }
                        ],
                    }
                ],
                "mtu": 1400,
                "multiplexing": {
                    "level": "MULTIPLEXING_LOW",
                },
            }
        ],
        "activeProfile": "PCAtelegram_web",
    }


def mieru_mihomo_proxy(cfg: dict[str, Any]) -> str:
    host = public_host_for_notes()
    return "\n".join([
        "proxies:",
        "  - name: PCAtelegram_web Mieru",
        "    type: mieru",
        f"    server: {host}",
        f"    port: {int(cfg['port'])}",
        f"    transport: {cfg['protocol']}",
        f"    username: {cfg['user']}",
        f"    password: {cfg['password']}",
        "    multiplexing: MULTIPLEXING_LOW",
        "",
    ])


def ensure_mieru_subscription_token(cfg: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    token = str(cfg.get("subscription_token") or "").strip()
    if len(token) >= 24 and re.match(r"^[A-Za-z0-9_-]+$", token):
        return cfg, False
    next_cfg = dict(cfg)
    next_cfg["subscription_token"] = secrets.token_urlsafe(24)
    write_mieru_config(next_cfg)
    return read_mieru_config(), True


def admin_public_base_url() -> str:
    host = public_host_for_notes()
    scheme = "http"
    return f"{scheme}://{host}:{PORT}"


def mieru_subscription_path(cfg: dict[str, Any]) -> str:
    token = str(cfg.get("subscription_token") or "").strip()
    return f"/sub/mieru/{urllib.parse.quote(token, safe='')}.yaml" if token else ""


def mieru_subscription_url(cfg: dict[str, Any]) -> str:
    path = mieru_subscription_path(cfg)
    return f"{admin_public_base_url()}{path}" if path else ""


def mieru_clash_import_url(cfg: dict[str, Any]) -> str:
    url = mieru_subscription_url(cfg)
    return f"clash://install-config?url={urllib.parse.quote(url, safe='')}" if url else ""


def public_mieru_config() -> dict[str, Any]:
    cfg = read_mieru_config()
    if cfg["password"]:
        cfg, _ = ensure_mieru_subscription_token(cfg)
    listeners, errors = collect_port_listeners(cfg["port"])
    conflicts = mieru_port_conflicts(cfg["port"], cfg["protocol"])
    status_text = mieru_status_text()
    installed = mieru_installed()
    running = installed and ("RUNNING" in status_text.upper() or any(
        str(item.get("proto") or "").upper() == cfg["protocol"]
        and ("mita" in str(item.get("process") or "").lower() or "mieru" in str(item.get("process") or "").lower())
        for item in listeners
    ))
    return {
        "enabled": cfg["enabled"],
        "installed": installed,
        "running": running,
        "service": service_status("mita"),
        "status_text": status_text,
        "port": cfg["port"],
        "protocol": cfg["protocol"],
        "user": cfg["user"],
        "password": cfg["password"],
        "password_mask": mask_secret(cfg["password"]),
        "updated_at": cfg["updated_at"],
        "listeners": listeners,
        "conflicts": conflicts,
        "ok": not errors,
        "error": "; ".join(errors[:2]),
        "client_config": mieru_client_config(cfg) if cfg["password"] else {},
        "mihomo_yaml": mieru_mihomo_proxy(cfg) if cfg["password"] else "",
        "subscription_url": mieru_subscription_url(cfg) if cfg["password"] else "",
        "clash_import_url": mieru_clash_import_url(cfg) if cfg["password"] else "",
    }


def latest_mita_asset_url() -> tuple[str, str]:
    req = urllib.request.Request(
        "https://api.github.com/repos/enfein/mieru/releases/latest",
        headers={"User-Agent": "PCAtelegram_web-admin"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        release = json.loads(resp.read(1024 * 1024).decode("utf-8"))
    assets = release.get("assets") if isinstance(release, dict) else []
    if not isinstance(assets, list):
        raise RuntimeError("invalid Mieru release metadata")
    machine = os.uname().machine.lower()
    arch_aliases = ["amd64", "x86_64"] if machine in {"x86_64", "amd64"} else ["arm64", "aarch64"] if machine in {"aarch64", "arm64"} else [machine]
    if shutil.which("apt-get") or shutil.which("dpkg"):
        extensions = [".deb"]
    elif shutil.which("dnf") or shutil.which("yum") or shutil.which("rpm"):
        extensions = [".rpm"]
    else:
        raise RuntimeError("supported package manager not found")
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        url = str(asset.get("browser_download_url") or "")
        if not url or ".sha256" in name:
            continue
        if not any(name.endswith(ext) for ext in extensions):
            continue
        if "mita" not in name:
            continue
        if any(alias in name for alias in arch_aliases):
            return url, name
    raise RuntimeError(f"mita package for {machine} not found in latest Mieru release")


def download_file(url: str, target: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "PCAtelegram_web-admin"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        target.write_bytes(resp.read())


def install_mita_package() -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": False, "installed": mieru_installed(), "asset": "", "warnings": []}
    if result["installed"] and shutil.which("mita"):
        return result
    if os.geteuid() != 0:
        result["warnings"].append("root required to install mita")
        return result
    url, name = latest_mita_asset_url()
    target = Path("/tmp") / name
    download_file(url, target)
    result.update({"attempted": True, "asset": name})
    if name.endswith(".deb"):
        run(["apt-get", "update"], timeout=180)
        code, _, err = run(["dpkg", "-i", str(target)], timeout=120)
        if code != 0:
            run(["apt-get", "install", "-f", "-y"], timeout=240)
    elif name.endswith(".rpm"):
        rpm = shutil.which("rpm")
        if not rpm:
            raise RuntimeError("rpm not found")
        code, _, err = run([rpm, "-Uvh", "--force", str(target)], timeout=180)
        if code != 0:
            raise RuntimeError(err.strip() or "rpm install failed")
    run(["systemctl", "enable", "--now", "mita"], timeout=30)
    result["installed"] = bool(shutil.which("mita")) or service_status("mita") != "not_installed"
    if not result["installed"]:
        result["warnings"].append("mita still not available after install")
    return result


def apply_mieru_config(cfg: dict[str, Any]) -> dict[str, Any]:
    server_cfg = mieru_server_config(cfg)
    MIERU_SERVER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MIERU_SERVER_CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(server_cfg, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(MIERU_SERVER_CONFIG_FILE)
    mita = shutil.which("mita")
    if not mita:
        raise RuntimeError("mita is not installed")
    code, out, err = run([mita, "apply", "config", str(MIERU_SERVER_CONFIG_FILE)], timeout=30)
    if code != 0:
        raise RuntimeError(err.strip() or out.strip() or "mita apply config failed")
    run([mita, "stop"], timeout=20)
    code, out, err = run([mita, "start"], timeout=30)
    if code != 0:
        raise RuntimeError(err.strip() or out.strip() or "mita start failed")
    return {"applied": True, "status": mieru_status_text()}


def save_mieru_settings(body: dict[str, Any]) -> dict[str, Any]:
    current = read_mieru_config()
    port = normalize_mieru_port(body.get("port") or current["port"])
    protocol = normalize_mieru_protocol(body.get("protocol") or current["protocol"])
    user = str(body.get("user") or current["user"] or "main").strip()
    if not USER_RE.match(user):
        raise ValueError("invalid Mieru user")
    password = str(body.get("password") or "").strip() or current.get("password") or secrets.token_urlsafe(18)
    conflicts = mieru_port_conflicts(port, protocol)
    if conflicts:
        names = ", ".join(f"{item.get('process')} {item.get('address')}" for item in conflicts[:3])
        raise RuntimeError(f"Mieru port is busy: {names}")
    install_result = install_mita_package()
    if not install_result.get("installed"):
        raise RuntimeError("; ".join(install_result.get("warnings") or ["mita install failed"]))
    cfg = {
        "enabled": True,
        "port": port,
        "protocol": protocol,
        "user": user,
        "password": password,
        "subscription_token": current.get("subscription_token") or secrets.token_urlsafe(24),
    }
    apply_result = apply_mieru_config(cfg)
    write_mieru_config(cfg)
    payload = public_mieru_config()
    payload["install"] = install_result
    payload["apply"] = apply_result
    return payload


def control_mieru(action: str) -> dict[str, Any]:
    if not mieru_installed():
        raise RuntimeError("mita is not installed")
    mita = shutil.which("mita")
    if not mita:
        raise RuntimeError("mita command not found")
    cfg = read_mieru_config()
    if action == "stop":
        code, out, err = run([mita, "stop"], timeout=20)
        cfg["enabled"] = False
        write_mieru_config(cfg)
    elif action == "start":
        if not cfg.get("password"):
            raise RuntimeError("Mieru config is empty")
        code, out, err = run([mita, "start"], timeout=30)
        cfg["enabled"] = code == 0
        write_mieru_config(cfg)
    elif action == "restart":
        if cfg.get("password"):
            apply_mieru_config(cfg)
            return public_mieru_config()
        code, out, err = run(["systemctl", "restart", "mita"], timeout=30)
    else:
        raise ValueError("unsupported Mieru action")
    if code != 0:
        raise RuntimeError(err.strip() or out.strip() or f"mita {action} failed")
    return public_mieru_config()


def read_disabled_users() -> dict[str, str]:
    raw = load_json(DISABLED_USERS_FILE, {}) or {}
    if not isinstance(raw, dict):
        return {}
    users = raw.get("users") if isinstance(raw.get("users"), dict) else raw
    if not isinstance(users, dict):
        return {}
    clean: dict[str, str] = {}
    for name, secret in users.items():
        if name in {"version", "updated_at"}:
            continue
        name_s = str(name).strip()
        secret_s = str(secret or "").strip()
        if USER_RE.match(name_s) and secret_s:
            clean[name_s] = secret_s
    return clean


def write_disabled_users(users: dict[str, str]) -> None:
    payload = {
        "version": 1,
        "updated_at": utc_now(),
        "users": {name: users[name] for name in sorted(users)},
    }
    save_json(DISABLED_USERS_FILE, payload)


def read_user_records() -> dict[str, dict[str, Any]]:
    active = read_telemt_users()
    disabled = read_disabled_users()
    ip_limits = read_user_max_unique_ips()
    records: dict[str, dict[str, Any]] = {}
    for name, secret in disabled.items():
        records[name] = {"secret": secret, "enabled": False, "max_unique_ips": ip_limits.get(name, 0)}
    for name, secret in active.items():
        records[name] = {"secret": secret, "enabled": True, "max_unique_ips": ip_limits.get(name, 0)}
    return records


def _ordered_user_lines(users: dict[str, str]) -> list[str]:
    names = []
    if "main" in users:
        names.append("main")
    names.extend(sorted(n for n in users if n != "main"))
    return [f'{quote_toml_key(name)} = "{users[name]}"' for name in names]


def _ordered_user_int_lines(values: dict[str, int]) -> list[str]:
    positive: dict[str, int] = {}
    for name, value in values.items():
        name_s = str(name)
        if not USER_RE.match(name_s):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            positive[name_s] = number
    names = []
    if "main" in positive:
        names.append("main")
    names.extend(sorted(n for n in positive if n != "main"))
    return [f'{quote_toml_key(name)} = {positive[name]}' for name in names]


def parse_toml_key(raw: str) -> str:
    key = raw.strip()
    if len(key) >= 2 and key[0] == key[-1] == '"':
        try:
            return json.loads(key)
        except json.JSONDecodeError:
            return key[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(key) >= 2 and key[0] == key[-1] == "'":
        return key[1:-1]
    return key


def quote_toml_key(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_telemt_users(users: dict[str, str]) -> None:
    TELEMT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    lines = TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines() if TELEMT_CONFIG.exists() else []
    rendered = _ordered_user_lines(users)
    out: list[str] = []
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

    tmp = TELEMT_CONFIG.with_name(TELEMT_CONFIG.name + ".tmp")
    tmp.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(TELEMT_CONFIG)


def write_toml_int_table(table: str, values: dict[str, int]) -> None:
    TELEMT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    lines = TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines() if TELEMT_CONFIG.exists() else []
    rendered = _ordered_user_int_lines(values)
    header = f"[{table}]"
    out: list[str] = []
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

    tmp = TELEMT_CONFIG.with_name(TELEMT_CONFIG.name + ".tmp")
    tmp.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(TELEMT_CONFIG)


def write_user_max_unique_ips(values: dict[str, int]) -> None:
    write_toml_int_table("access.user_max_unique_ips", values)


def normalize_max_unique_ips(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("max_unique_ips must be an integer") from None
    if number < 0 or number > MAX_UNIQUE_IP_LIMIT:
        raise ValueError(f"max_unique_ips must be between 0 and {MAX_UNIQUE_IP_LIMIT}")
    return number


def restart_service(name: str) -> bool:
    code, _, _ = run(["systemctl", "restart", name], timeout=25)
    if code != 0:
        return False
    if name == "telemt":
        return wait_tcp_port(read_telemt_port(), timeout=90)
    return True


def request_service_restart(name: str) -> bool:
    global _LAST_TELEMT_RESTART
    if name == "telemt":
        now = time.monotonic()
        if _LAST_TELEMT_RESTART > 0 and now - _LAST_TELEMT_RESTART < TELEMT_RESTART_DEBOUNCE_SECONDS:
            status = service_status(name)
            if status in {"running", "activating"}:
                return True
        run(["systemctl", "reset-failed", name], timeout=5)
        _LAST_TELEMT_RESTART = now
    code, _, _ = run(["systemctl", "--no-block", "restart", name], timeout=5)
    return code == 0


def service_status(name: str) -> str:
    code, stdout, _ = run(["systemctl", "is-active", name], timeout=3)
    value = stdout.strip()
    if code == 0 and value == "active":
        return "running"
    code, stdout, _ = run(["systemctl", "list-unit-files", f"{name}.service", "--no-legend"], timeout=3)
    if code != 0 or not stdout.strip():
        return "not_installed"
    if value in {"failed", "inactive", "activating", "deactivating"}:
        return value
    return "stopped"


def read_telemt_port() -> int:
    if not TELEMT_CONFIG.exists():
        return 443
    in_server = False
    for raw in TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line == "[server]":
            in_server = True
            continue
        if in_server and line.startswith("["):
            break
        if in_server and line.startswith("port") and "=" in line:
            try:
                return int(line.split("=", 1)[1].strip().split("#", 1)[0])
            except ValueError:
                return 443
    return 443


def _is_port_addr(value: str, port: int) -> bool:
    token = value.strip()
    if token.startswith("[") and "]:" in token:
        return token.rsplit(":", 1)[-1] == str(port)
    return token.rsplit(":", 1)[-1] == str(port) if ":" in token else False


def _process_role(process: str) -> str:
    lowered = process.lower()
    if "telemt" in lowered or "mtproto" in lowered:
        return "mtproxy"
    if "mita" in lowered or "mieru" in lowered:
        return "mieru"
    if "nginx" in lowered or "apache" in lowered or "caddy" in lowered:
        return "site"
    if "xray" in lowered or "x-ui" in lowered or "3x-ui" in lowered or "xui" in lowered:
        return "xray"
    if "amnezia" in lowered or "awg" in lowered or "wireguard" in lowered or re.search(r"\bwg\b", lowered):
        return "amneziawg"
    return "other"


def parse_ss_listeners(output: str, proto: str, port: int = 443) -> list[dict[str, Any]]:
    listeners: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for line in output.splitlines():
        parts = line.split()
        address = next((part for part in parts if _is_port_addr(part, port)), "")
        if not address:
            continue
        matches = re.findall(r'\("([^"]+)",pid=(\d+)', line)
        if matches:
            process_names = []
            pids = []
            for proc, pid in matches:
                if proc not in process_names:
                    process_names.append(proc)
                if pid not in pids:
                    pids.append(pid)
            process = ", ".join(process_names)
            pid_text = ", ".join(pids)
        else:
            process = "unknown"
            pid_text = ""
        key = (proto, address, process)
        if key in seen:
            continue
        seen.add(key)
        listeners.append({
            "proto": proto.upper(),
            "address": address,
            "process": process,
            "pid": pid_text,
            "role": _process_role(process),
        })
    return listeners


def collect_port_listeners(port: int) -> tuple[list[dict[str, Any]], list[str]]:
    listeners: list[dict[str, Any]] = []
    errors: list[str] = []
    for proto, args in {
        "tcp": ["ss", "-H", "-ltnp"],
        "udp": ["ss", "-H", "-lunp"],
    }.items():
        code, stdout, stderr = run(args, timeout=2)
        if code == 0:
            listeners.extend(parse_ss_listeners(stdout, proto, port))
        elif stderr.strip():
            errors.append(stderr.strip())
    listeners.sort(key=lambda item: (item["proto"], item["address"], item["process"]))
    return listeners, errors


def read_telemt_edge_settings() -> dict[str, Any]:
    settings: dict[str, Any] = {"tls_domain": "", "mask_port": 0, "dns_overrides": []}
    if not TELEMT_CONFIG.exists():
        return settings
    section = ""
    for raw in TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().split("#", 1)[0].strip()
        if section == "censorship" and key == "tls_domain":
            settings["tls_domain"] = value.strip('"').strip("'")
        elif section == "censorship" and key == "mask_port":
            try:
                settings["mask_port"] = int(value)
            except ValueError:
                settings["mask_port"] = 0
        elif section == "network" and key == "dns_overrides":
            settings["dns_overrides"] = re.findall(r'"([^"]+)"', value)
    return settings


def normalize_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise ValueError("port must be a number") from None
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return port


def normalize_mask_host(value: Any) -> str:
    host = str(value or "").strip().lower().rstrip(".")
    if not HOST_RE.match(host):
        raise ValueError("mask site must be a valid domain")
    return host


def update_toml_scalar(section: str, key: str, literal: str) -> None:
    TELEMT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    lines = TELEMT_CONFIG.read_text(encoding="utf-8", errors="ignore").splitlines() if TELEMT_CONFIG.exists() else []
    header = f"[{section}]"
    out: list[str] = []
    current = ""
    found_section = False
    wrote_key = False

    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current == section and not wrote_key:
                out.append(f"{key} = {literal}")
                wrote_key = True
            current = stripped.strip("[]")
            if stripped == header:
                found_section = True
            out.append(raw)
            continue
        if current == section and stripped.startswith(key) and "=" in stripped:
            out.append(f"{key} = {literal}")
            wrote_key = True
            continue
        out.append(raw)

    if not found_section:
        if out and out[-1].strip():
            out.append("")
        out.append(header)
        out.append(f"{key} = {literal}")
    elif current == section and not wrote_key:
        out.append(f"{key} = {literal}")

    tmp = TELEMT_CONFIG.with_name(TELEMT_CONFIG.name + ".tmp")
    tmp.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(TELEMT_CONFIG)


def routing_payload(port: int | None = None) -> dict[str, Any]:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    settings = read_telemt_edge_settings()
    current_port = int(port or config.get("port") or read_telemt_port() or 443)
    mask_host = str(config.get("mask_host") or settings.get("tls_domain") or "google.com")
    listeners, errors = collect_port_listeners(current_port)
    conflicts = [
        item for item in listeners
        if item.get("role") != "mtproxy" and "telemt" not in str(item.get("process", "")).lower()
    ]
    return {
        "port": current_port,
        "mask_host": mask_host,
        "mask_port": int(settings.get("mask_port") or 443),
        "mode": str(config.get("mode") or "lite"),
        "domain": str(config.get("domain") or ""),
        "listeners": listeners,
        "conflicts": conflicts,
        "ok": not errors,
        "error": "; ".join(errors[:2]),
        "per_user_ports_supported": False,
        "note": "telemt has one server.port per instance; real per-client ports need multiple telemt services.",
    }


def ensure_main_user(users: dict[str, str] | None = None) -> tuple[dict[str, str], bool]:
    current = dict(users if users is not None else read_telemt_users())
    if current:
        return current, False
    seed = f"main:{time.time()}:{secrets.token_hex(32)}".encode()
    current["main"] = hashlib.sha256(seed).hexdigest()[:32]
    write_telemt_users(current)
    return current, True


def sync_routing_config(port: int, mask_host: str, users: dict[str, str]) -> None:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    if not isinstance(config, dict):
        config = {}
    config["engine"] = "telemt"
    config["mode"] = str(config.get("mode") or "lite")
    config["port"] = port
    config["mask_host"] = mask_host
    if "main" in users:
        config["secret"] = users["main"]
    config["updated_at"] = utc_now()
    save_json(PCATELEGRAM_WEB_CONFIG, config)


def install_telemt_for_routing(port: int, mask_host: str, users: dict[str, str]) -> None:
    main_secret = users.get("main") or next(iter(users.values()), "")
    if not main_secret:
        raise RuntimeError("no telemt user secret")
    script = """
set -euo pipefail
cd /opt/pcatelegram_web
source /opt/pcatelegram_web/lib/common.sh
source /opt/pcatelegram_web/lib/i18n.sh
source /opt/pcatelegram_web/lib/telemt.sh
source /opt/pcatelegram_web/lib/telemt_config.sh
load_language "$(detect_language 2>/dev/null || echo en)" 2>/dev/null || true
ensure_deps >/tmp/pcatelegram_web-ensure-deps.log 2>&1 || true
install_telemt_full >/tmp/pcatelegram_web-telemt-install.log 2>&1
generate_telemt_toml "$PCAT_MAIN_SECRET" "$PCAT_PORT" "lite" "$PCAT_MASK_HOST" "443" >/tmp/pcatelegram_web-telemt-config.log 2>&1
validate_telemt_config >/tmp/pcatelegram_web-telemt-validate.log 2>&1
start_telemt >/tmp/pcatelegram_web-telemt-start.log 2>&1
"""
    code, _, stderr = run_bash_env(
        script,
        {
            "PCAT_MAIN_SECRET": main_secret,
            "PCAT_PORT": str(port),
            "PCAT_MASK_HOST": mask_host,
        },
        timeout=240,
    )
    if code != 0:
        raise RuntimeError((stderr.strip().splitlines()[-1:] or ["telemt install failed"])[0])


def write_routing_settings(port: int, mask_host: str) -> dict[str, Any]:
    listeners, _ = collect_port_listeners(port)
    conflicts = [
        item for item in listeners
        if item.get("role") != "mtproxy" and "telemt" not in str(item.get("process", "")).lower()
    ]
    if conflicts:
        names = ", ".join(f"{item.get('process')} {item.get('address')}" for item in conflicts[:3])
        raise RuntimeError(f"port is busy: {names}")

    users, _ = ensure_main_user()
    if service_status("telemt") == "not_installed":
        install_telemt_for_routing(port, mask_host, users)
        sync_routing_config(port, mask_host, users)
        payload = routing_payload(port)
        payload["restart"] = {"requested": True, "installed": True}
        return payload

    update_toml_scalar("server", "port", str(port))
    update_toml_scalar("general.links", "public_port", str(port))
    update_toml_scalar("censorship", "tls_domain", json.dumps(mask_host))

    sync_routing_config(port, mask_host, users)

    restarted = False
    status = service_status("telemt")
    if status != "not_installed":
        restarted = request_service_restart("telemt")
    payload = routing_payload(port)
    payload["restart"] = {"requested": restarted, "installed": False}
    return payload


def load_shared443_config() -> dict[str, Any]:
    raw = load_json(SHARED_443_CONFIG, {}) or {}
    if not isinstance(raw, dict):
        return {}
    routes = raw.get("xray_routes") if isinstance(raw.get("xray_routes"), list) else []
    clean_routes = []
    for item in routes:
        if not isinstance(item, dict):
            continue
        public = str(item.get("public") or item.get("domain") or "").strip()
        target = str(item.get("target") or "").strip()
        if public and target:
            clean_routes.append({"public": public, "target": target})
    return {
        "enabled": bool(raw.get("enabled")),
        "dispatcher": str(raw.get("dispatcher") or "nginx-stream"),
        "public_port": _int_value(raw.get("public_port") or 443) or 443,
        "telemt_target": str(raw.get("telemt_target") or "127.0.0.1:7443"),
        "site_target": str(raw.get("site_target") or ""),
        "xray_routes": clean_routes,
        "updated_at": str(raw.get("updated_at") or ""),
    }


def listener_for_target(target: str) -> dict[str, Any] | None:
    try:
        port = int(target.rsplit(":", 1)[-1])
    except ValueError:
        return None
    listeners, _ = collect_port_listeners(port)
    return listeners[0] if listeners else None


def routed_behind_443() -> list[dict[str, Any]]:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    mode = str(config.get("mode") or "")
    domain = str(config.get("domain") or "")
    settings = read_telemt_edge_settings()
    shared = load_shared443_config()
    mask_port = int(settings.get("mask_port") or 0)
    tls_domain = str(settings.get("tls_domain") or domain)
    routes: list[dict[str, Any]] = []
    if shared.get("enabled"):
        telemt_target = str(shared.get("telemt_target") or "127.0.0.1:7443")
        telemt_listener = listener_for_target(telemt_target)
        routes.append({
            "role": "mtproxy",
            "proto": "MTProxy",
            "public": f"{domain or tls_domain or 'default'}:443",
            "target": telemt_target,
            "process": (telemt_listener or {}).get("process") or "telemt",
            "pid": (telemt_listener or {}).get("pid") or "",
            "status": service_status("telemt"),
            "via": "nginx stream ssl_preread",
            "tls_domain": tls_domain,
            "details": ["default -> telemt"] if not shared.get("xray_routes") else [],
        })
        for item in shared.get("xray_routes", []):
            target = item.get("target", "")
            listener = listener_for_target(target)
            public = item.get("public", "")
            if public and ":" not in public:
                public = f"{public}:443"
            routes.append({
                "role": "xray",
                "proto": "VLESS",
                "public": public or "xray:443",
                "target": target,
                "process": (listener or {}).get("process") or "xray",
                "pid": (listener or {}).get("pid") or "",
                "status": "running" if listener else "not_installed",
                "via": "nginx stream ssl_preread",
                "tls_domain": public.split(":", 1)[0] if public else "",
                "details": [],
            })
    if mode == "pro" and domain and mask_port and mask_port != 443:
        internal, _ = collect_port_listeners(mask_port)
        site_listener = next((item for item in internal if item.get("role") == "site"), None)
        routes.append({
            "role": "site",
            "proto": "HTTPS",
            "public": f"{domain}:443",
            "target": f"127.0.0.1:{mask_port}",
            "process": (site_listener or {}).get("process") or "nginx",
            "pid": (site_listener or {}).get("pid") or "",
            "status": service_status("nginx"),
            "via": "telemt dns_overrides",
            "tls_domain": tls_domain,
            "details": settings.get("dns_overrides") or [],
        })
    return routes


def port_status(port: int | None = None) -> dict[str, Any]:
    public_port = int(port or read_telemt_port() or 443)
    listeners, errors = collect_port_listeners(public_port)
    shared = load_shared443_config()
    if public_port == 443 and shared.get("enabled"):
        for item in listeners:
            if item.get("role") == "site" and "nginx" in str(item.get("process", "")).lower():
                item["role"] = "edge"
                item["details"] = "nginx stream ssl_preread"
    return {
        "checked_at": int(time.time()),
        "public_port": public_port,
        "configured_port": read_telemt_port(),
        "listeners": listeners,
        "routes": routed_behind_443() if public_port == 443 else [],
        "shared_443": shared,
        "ok": not errors,
        "error": "; ".join(errors[:2]),
    }


def port_443_status() -> dict[str, Any]:
    return port_status(443)


def wait_tcp_port(port: int, timeout: int = 90) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service_status("telemt") not in {"running", "activating"}:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.6):
                return True
        except OSError:
            time.sleep(1)
    return False


def public_ip() -> str:
    code, stdout, _ = run(["curl", "-s", "-4", "--max-time", "3", "https://api.ipify.org"], timeout=5)
    ip = stdout.strip()
    if code == 0 and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        return ip
    code, stdout, _ = run(["hostname", "-I"], timeout=3)
    return stdout.split()[0] if code == 0 and stdout.split() else "0.0.0.0"


def proxy_link(secret: str) -> str:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    mode = str(config.get("mode", "lite"))
    port = int(config.get("port", 443) or 443)
    domain = str(config.get("domain", "") or "")
    mask_host = str(config.get("mask_host", "") or "")

    if mode == "pro" and domain:
        link_mask = mask_host or domain
        host_hex = link_mask.encode().hex()
        return f"tg://proxy?server={domain}&port={port}&secret=ee{secret}{host_hex}"

    server = public_ip()
    if mask_host:
        host_hex = mask_host.encode().hex()
        return f"tg://proxy?server={server}&port={port}&secret=ee{secret}{host_hex}"
    return f"tg://proxy?server={server}&port={port}&secret={secret}"


def telemt_api(path: str) -> Any:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:9091{path}", timeout=1.8) as resp:
            payload = resp.read(256 * 1024)
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def site_status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    host = str(config.get("domain") or "").strip()
    if not host:
        return {"host": "", "url": "", "http_code": 0, "ok": False, "checked": False, "error": "domain_missing"}
    if not re.match(r"^[A-Za-z0-9.-]{1,253}$", host) or ".." in host or host.startswith(".") or host.endswith("."):
        return {"host": host, "url": "", "http_code": 0, "ok": False, "checked": False, "error": "invalid_domain"}
    url = f"https://{host}/"
    code, stdout, stderr = run(["curl", "-k", "-L", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8", url], timeout=10)
    raw_code = stdout.strip()
    try:
        http_code = int(raw_code)
    except ValueError:
        http_code = 0
    return {
        "host": host,
        "url": url,
        "http_code": http_code,
        "ok": code == 0 and http_code == 200,
        "checked": True,
        "error": "" if code == 0 else (stderr.strip() or f"curl exit {code}"),
        "checked_at": int(time.time()),
    }


def default_mask_html(domain: str = "") -> str:
    title = "Информационный центр"
    subtitle = "Полезные материалы, новости и практические заметки для повседневной работы."
    host = domain or "local"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; --text:#1f2937; --muted:#667085; --line:#d8e0ec; --bg:#f5f7fb; --card:#ffffff; --blue:#2563eb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; min-height:100vh; font-family: Arial, sans-serif; background:var(--bg); color:var(--text); }}
    header, main, footer {{ width:min(980px, calc(100% - 32px)); margin:auto; }}
    header {{ padding:42px 0 22px; display:flex; justify-content:space-between; gap:20px; align-items:center; border-bottom:1px solid var(--line); }}
    .brand {{ font-size:22px; font-weight:800; }}
    nav {{ color:var(--muted); font-size:14px; }}
    .hero {{ padding:64px 0 44px; }}
    h1 {{ margin:0 0 18px; font-size:clamp(34px, 6vw, 64px); line-height:1; letter-spacing:0; }}
    p {{ margin:0; color:var(--muted); font-size:20px; line-height:1.6; max-width:720px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; margin:22px 0 70px; }}
    article {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:22px; box-shadow:0 18px 45px rgba(15,23,42,.08); }}
    h2 {{ margin:0 0 10px; font-size:20px; }}
    article p {{ font-size:15px; line-height:1.5; }}
    footer {{ padding:24px 0 36px; color:var(--muted); font-size:14px; border-top:1px solid var(--line); }}
    @media (max-width:760px) {{ header {{ align-items:flex-start; flex-direction:column; }} .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="brand">{title}</div>
    <nav>{host}</nav>
  </header>
  <main>
    <section class="hero">
      <h1>Коротко. Понятно. По делу.</h1>
      <p>{subtitle}</p>
    </section>
    <section class="grid" aria-label="Разделы">
      <article><h2>Материалы</h2><p>Подборки и инструкции для людей, которым нужен быстрый ответ без лишнего шума.</p></article>
      <article><h2>Обновления</h2><p>Заметки о полезных изменениях, сервисах и рабочих сценариях.</p></article>
      <article><h2>Контакты</h2><p>Предложения и вопросы можно отправить владельцу сайта удобным способом.</p></article>
    </section>
  </main>
  <footer>© {time.strftime("%Y")} {title}</footer>
</body>
</html>
"""


def write_site_domain(domain: str) -> None:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    if not isinstance(config, dict):
        config = {}
    config["domain"] = domain
    config["site_domain"] = domain
    config["site_updated_at"] = utc_now()
    save_json(PCATELEGRAM_WEB_CONFIG, config)


def site_port80_conflicts() -> list[dict[str, Any]]:
    listeners, _ = collect_port_listeners(80)
    return [
        item for item in listeners
        if "nginx" not in str(item.get("process", "")).lower()
    ]


def site_mask_status() -> dict[str, Any]:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    if not isinstance(config, dict):
        config = {}
    domain = str(config.get("site_domain") or config.get("domain") or "").strip()
    index = WEBSITE_ROOT / "index.html"
    listeners, errors = collect_port_listeners(80)
    installed = NGINX_MASK_LINK.exists() and index.exists()
    return {
        "domain": domain,
        "url": f"http://{domain}/" if domain else "",
        "installed": installed,
        "nginx": service_status("nginx"),
        "port": 80,
        "listeners": listeners,
        "conflicts": site_port80_conflicts(),
        "html_exists": index.exists(),
        "html_size": index.stat().st_size if index.exists() else 0,
        "html_mtime": int(index.stat().st_mtime) if index.exists() else 0,
        "ok": not errors,
        "error": "; ".join(errors[:2]),
        "checked_at": int(time.time()),
    }


def write_mask_nginx_config(domain: str) -> None:
    server_name = domain if domain else "_"
    NGINX_MASK_CONF.parent.mkdir(parents=True, exist_ok=True)
    NGINX_MASK_LINK.parent.mkdir(parents=True, exist_ok=True)
    conf = f"""# PCAtelegram_web public mask site on port 80
server {{
    listen 80;
    listen [::]:80;
    server_name {server_name};

    root {WEBSITE_ROOT};
    index index.html;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location ~ /\\. {{
        deny all;
    }}
}}
"""
    tmp = NGINX_MASK_CONF.with_suffix(".tmp")
    tmp.write_text(conf, encoding="utf-8")
    os.chmod(tmp, 0o644)
    tmp.replace(NGINX_MASK_CONF)
    try:
        Path("/etc/nginx/sites-enabled/default").unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
    if NGINX_MASK_LINK.exists() or NGINX_MASK_LINK.is_symlink():
        NGINX_MASK_LINK.unlink()
    NGINX_MASK_LINK.symlink_to(NGINX_MASK_CONF)


def install_mask_site(domain: str, html: str = "") -> dict[str, Any]:
    if domain and not HOST_RE.match(domain):
        raise ValueError("domain must be a valid domain or empty")
    conflicts = site_port80_conflicts()
    if conflicts:
        names = ", ".join(f"{item.get('process')} {item.get('address')}" for item in conflicts[:3])
        raise RuntimeError(f"port 80 is busy: {names}")
    if html and len(html.encode("utf-8")) > 1024 * 1024:
        raise ValueError("html file is too large")
    if not html:
        html = default_mask_html(domain)
    WEBSITE_ROOT.mkdir(parents=True, exist_ok=True)
    index = WEBSITE_ROOT / "index.html"
    tmp = index.with_suffix(".tmp")
    tmp.write_text(html, encoding="utf-8")
    os.chmod(tmp, 0o644)
    tmp.replace(index)
    write_site_domain(domain)
    script = """
set -euo pipefail
source /opt/pcatelegram_web/lib/common.sh
source /opt/pcatelegram_web/lib/i18n.sh
source /opt/pcatelegram_web/lib/website.sh
load_language "$(detect_language 2>/dev/null || echo en)" 2>/dev/null || true
ensure_deps >/tmp/pcatelegram_web-site-ensure-deps.log 2>&1 || true
install_nginx >/tmp/pcatelegram_web-site-nginx-install.log 2>&1
"""
    code, _, stderr = run_bash_env(script, timeout=180)
    if code != 0:
        raise RuntimeError((stderr.strip().splitlines()[-1:] or ["nginx install failed"])[0])
    write_mask_nginx_config(domain)
    code, _, stderr = run(["nginx", "-t"], timeout=10)
    if code != 0:
        raise RuntimeError(stderr.strip() or "nginx config test failed")
    code, _, stderr = run(["systemctl", "restart", "nginx"], timeout=30)
    if code != 0:
        raise RuntimeError(stderr.strip() or "nginx restart failed")
    return site_mask_status()


def remove_mask_site() -> dict[str, Any]:
    if NGINX_MASK_LINK.exists() or NGINX_MASK_LINK.is_symlink():
        NGINX_MASK_LINK.unlink()
    if NGINX_MASK_CONF.exists():
        NGINX_MASK_CONF.unlink()
    code, _, _ = run(["nginx", "-t"], timeout=10)
    if code == 0:
        run(["systemctl", "reload", "nginx"], timeout=15)
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    if isinstance(config, dict):
        config["site_enabled"] = False
        config["site_updated_at"] = utc_now()
        save_json(PCATELEGRAM_WEB_CONFIG, config)
    return site_mask_status()


def load_stats_history(limit: int | None = 240) -> list[dict[str, int]]:
    if not HISTORY_FILE.exists():
        return []
    rows: list[dict[str, int]] = []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    rows.append({
                        "epoch": int(row.get("epoch") or 0),
                        "proxy_bytes": int(row.get("proxy_bytes") or 0),
                        "site_bytes": int(row.get("site_bytes") or 0),
                    })
                except ValueError:
                    continue
    except OSError:
        return []
    if limit:
        rows = rows[-limit:]
    previous = None
    enriched: list[dict[str, int]] = []
    for row in rows:
        item = dict(row)
        if previous:
            item["proxy_delta"] = max(0, row["proxy_bytes"] - previous["proxy_bytes"])
            item["site_delta"] = max(0, row["site_bytes"] - previous["site_bytes"])
        else:
            item["proxy_delta"] = 0
            item["site_delta"] = 0
        enriched.append(item)
        previous = row
    return enriched


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def load_user_stats_history(name: str | None = None, limit: int | None = 240) -> list[dict[str, Any]]:
    if not USER_HISTORY_FILE.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with USER_HISTORY_FILE.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                user = str(row.get("user") or "").strip()
                if name is not None and user != name:
                    continue
                if not USER_RE.match(user):
                    continue
                rows.append({
                    "epoch": _int_value(row.get("epoch")),
                    "user": user,
                    "total_octets": _int_value(row.get("total_octets")),
                    "current_connections": _int_value(row.get("current_connections")),
                    "active_unique_ips": _int_value(row.get("active_unique_ips")),
                    "recent_unique_ips": _int_value(row.get("recent_unique_ips")),
                })
    except OSError:
        return []
    rows.sort(key=lambda item: (item["user"], item["epoch"]))
    if limit and name is not None:
        rows = rows[-limit:]

    previous_by_user: dict[str, dict[str, Any]] = {}
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        previous = previous_by_user.get(row["user"])
        item["total_delta"] = max(0, row["total_octets"] - previous["total_octets"]) if previous else 0
        enriched.append(item)
        previous_by_user[row["user"]] = row
    if limit and name is None:
        enriched = enriched[-limit:]
    return enriched


def latest_user_stats() -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not USER_HISTORY_FILE.exists():
        return latest
    try:
        with USER_HISTORY_FILE.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                user = str(row.get("user") or "").strip()
                if not USER_RE.match(user):
                    continue
                item = {
                    "epoch": _int_value(row.get("epoch")),
                    "user": user,
                    "total_octets": _int_value(row.get("total_octets")),
                    "current_connections": _int_value(row.get("current_connections")),
                    "active_unique_ips": _int_value(row.get("active_unique_ips")),
                    "recent_unique_ips": _int_value(row.get("recent_unique_ips")),
                }
                if item["epoch"] >= latest.get(user, {}).get("epoch", 0):
                    latest[user] = item
    except OSError:
        return {}
    return latest


def runtime_user_traffic(name: str, enabled: bool = True) -> dict[str, Any]:
    if not enabled:
        return {"ok": False, "enabled": False, "total_octets": 0, "current_connections": 0, "active_unique_ips": 0, "recent_unique_ips": 0}
    payload = telemt_api(f"/v1/users/{urllib.parse.quote(name, safe='')}")
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    return {
        "ok": bool(payload),
        "enabled": True,
        "total_octets": _int_value(data.get("total_octets")),
        "current_connections": _int_value(data.get("current_connections")),
        "active_unique_ips": _int_value(data.get("active_unique_ips")),
        "recent_unique_ips": _int_value(data.get("recent_unique_ips")),
        "in_runtime": bool(data.get("in_runtime")) if data else False,
    }


def current_user_traffic_snapshot(
    name: str,
    enabled: bool,
    history_snapshot: dict[str, Any] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    """Return live counters for key cards, preserving only total bytes from history.

    History rows are minute snapshots. They are useful for charts, but stale
    connection/IP values make the keys list look like users are still online.
    """
    history_snapshot = history_snapshot or {}
    fallback = {
        "epoch": _int_value(history_snapshot.get("epoch")),
        "total_octets": _int_value(history_snapshot.get("total_octets")),
        "current_connections": 0,
        "active_unique_ips": 0,
        "recent_unique_ips": 0,
    }
    if not enabled:
        return fallback
    runtime = runtime_user_traffic(name, enabled)
    if not runtime.get("ok"):
        return fallback
    return {
        "epoch": _int_value(now if now is not None else time.time()),
        "total_octets": _int_value(runtime.get("total_octets")),
        "current_connections": _int_value(runtime.get("current_connections")),
        "active_unique_ips": _int_value(runtime.get("active_unique_ips")),
        "recent_unique_ips": _int_value(runtime.get("recent_unique_ips")),
    }


def history_limit_for_range(range_key: str) -> int:
    return {
        "15m": 180,
        "1h": 240,
        "24h": 1800,
        "month": 50000,
    }.get(range_key, 240)


def normalize_range(range_key: str) -> str:
    return range_key if range_key in TRAFFIC_WINDOWS else "1h"


def filter_history_by_range(rows: list[dict[str, int]], range_key: str) -> list[dict[str, int]]:
    if not rows:
        return []
    seconds = TRAFFIC_WINDOWS[normalize_range(range_key)]
    latest = max(row.get("epoch", 0) for row in rows)
    cutoff = latest - seconds
    return [row for row in rows if row.get("epoch", 0) >= cutoff]


def traffic_interval_summaries(rows: list[dict[str, int]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {"range": key, "points": 0, "from": 0, "to": 0, "proxy_delta": 0, "site_delta": 0, "proxy_total": 0, "site_total": 0}
            for key in TRAFFIC_WINDOWS
        ]
    latest = max(row.get("epoch", 0) for row in rows)
    summaries = []
    for key, seconds in TRAFFIC_WINDOWS.items():
        window = [row for row in rows if row.get("epoch", 0) >= latest - seconds]
        if not window:
            summaries.append({"range": key, "points": 0, "from": 0, "to": latest, "proxy_delta": 0, "site_delta": 0, "proxy_total": 0, "site_total": 0})
            continue
        first = window[0]
        last = window[-1]
        summaries.append({
            "range": key,
            "points": len(window),
            "from": first.get("epoch", 0),
            "to": last.get("epoch", 0),
            "proxy_delta": sum(max(0, int(item.get("proxy_delta", 0))) for item in window),
            "site_delta": sum(max(0, int(item.get("site_delta", 0))) for item in window),
            "proxy_total": int(last.get("proxy_bytes", 0)),
            "site_total": int(last.get("site_bytes", 0)),
        })
    return summaries


def user_traffic_interval_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return [
            {"range": key, "points": 0, "from": 0, "to": 0, "total_delta": 0, "total_octets": 0}
            for key in TRAFFIC_WINDOWS
        ]
    latest = max(row.get("epoch", 0) for row in rows)
    summaries = []
    for key, seconds in TRAFFIC_WINDOWS.items():
        window = [row for row in rows if row.get("epoch", 0) >= latest - seconds]
        if not window:
            summaries.append({"range": key, "points": 0, "from": 0, "to": latest, "total_delta": 0, "total_octets": 0})
            continue
        first = window[0]
        last = window[-1]
        summaries.append({
            "range": key,
            "points": len(window),
            "from": first.get("epoch", 0),
            "to": last.get("epoch", 0),
            "total_delta": sum(max(0, int(item.get("total_delta", 0))) for item in window),
            "total_octets": int(last.get("total_octets", 0)),
        })
    return summaries


def count_history_rows() -> int:
    if not HISTORY_FILE.exists():
        return 0
    try:
        with HISTORY_FILE.open("r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for line in fh if line and line[0].isdigit())
    except OSError:
        return 0


def count_user_history_rows(name: str | None = None) -> int:
    if not USER_HISTORY_FILE.exists():
        return 0
    try:
        with USER_HISTORY_FILE.open("r", encoding="utf-8", errors="ignore") as fh:
            if name is None:
                return sum(1 for line in fh if line and line[0].isdigit())
            return sum(1 for line in fh if line.startswith(tuple(str(d) for d in range(10))) and f",{name}," in line)
    except OSError:
        return 0


def stats_status(current: dict[str, Any] | None = None, history: list[dict[str, int]] | None = None) -> dict[str, Any]:
    current = current if current is not None else (load_json(CURRENT_STATS, {}) or {})
    history = history if history is not None else load_stats_history(limit=2)
    service = service_status("pcatelegram_web-stats")
    now = int(time.time())
    ts = int(current.get("ts") or 0) if isinstance(current, dict) else 0
    age = max(0, now - ts) if ts else None
    error = str(current.get("error") or "") if isinstance(current, dict) else ""
    history_rows = count_history_rows()
    if error:
        health = "error"
    elif service == "running" and current and age is not None and age <= 180:
        health = "ok"
    elif service == "running":
        health = "stale"
    elif service == "not_installed":
        health = "not_installed"
    else:
        health = "stopped"
    return {
        "health": health,
        "service": service,
        "current_exists": CURRENT_STATS.exists(),
        "history_exists": HISTORY_FILE.exists(),
        "history_rows": history_rows,
        "history_points": len(history or []),
        "last_ts": ts,
        "age_seconds": age,
        "error": error,
    }


def run_stats_action(action: str) -> tuple[bool, str, dict[str, Any]]:
    if action == "repair":
        body = (
            "source /opt/pcatelegram_web/lib/common.sh; "
            "source /opt/pcatelegram_web/lib/i18n.sh; "
            "source /opt/pcatelegram_web/lib/stats.sh; "
            "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
            "install_stats_collector; "
            "stats_collect"
        )
        timeout = 180
    else:
        body = (
            "source /opt/pcatelegram_web/lib/common.sh; "
            "source /opt/pcatelegram_web/lib/stats.sh; "
            "stats_init >/dev/null 2>&1 || true; "
            "stats_collect"
        )
        timeout = 30
    code, stdout, stderr = run(["bash", "-lc", body], timeout=timeout)
    message = (stdout.strip().splitlines()[-1:] or stderr.strip().splitlines()[-1:] or [""])[0]
    current = load_json(CURRENT_STATS, {}) or {}
    history = load_stats_history()
    return code == 0, message, {"current": current, "history": history, "status": stats_status(current, history)}


def list_backups() -> list[dict[str, Any]]:
    if not BACKUP_DIR.exists():
        return []
    items = []
    for path in sorted(BACKUP_DIR.glob("*.tar.gz*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.name.endswith(".sha256"):
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        items.append({
            "name": path.name,
            "path": str(path),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "encrypted": path.name.endswith(".enc"),
        })
    return items[:30]


def backup_schedule_calendar(frequency: str) -> str | None:
    calendars = {
        "off": None,
        "daily": "*-*-* 03:20:00",
        "weekly": "Sun 03:20:00",
        "monthly": "*-*-01 03:20:00",
    }
    if frequency not in calendars:
        raise ValueError("unsupported backup schedule")
    return calendars[frequency]


def backup_schedule_status() -> dict[str, Any]:
    raw = load_json(BACKUP_SCHEDULE_FILE, {}) or {}
    if not isinstance(raw, dict):
        raw = {}
    frequency = str(raw.get("frequency") or "off")
    try:
        calendar = backup_schedule_calendar(frequency)
    except ValueError:
        frequency = "off"
        calendar = None
    active_code, active, _ = run(["systemctl", "is-active", "pcatelegram_web-backup.timer"], timeout=5)
    enabled_code, enabled, _ = run(["systemctl", "is-enabled", "pcatelegram_web-backup.timer"], timeout=5)
    _, next_run, _ = run(["systemctl", "show", "pcatelegram_web-backup.timer", "--property=NextElapseUSecRealtime", "--value"], timeout=5)
    return {
        "frequency": frequency,
        "calendar": calendar,
        "enabled": enabled_code == 0 and enabled.strip() == "enabled",
        "active": active_code == 0 and active.strip() == "active",
        "next": next_run.strip(),
        "updated_at": raw.get("updated_at") or "",
    }


def set_backup_schedule(frequency: str) -> tuple[bool, str, dict[str, Any]]:
    backup_schedule_calendar(frequency)
    script = (
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/i18n.sh; "
        "source /opt/pcatelegram_web/lib/backup.sh; "
        "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
        f"set_backup_schedule {shlex.quote(frequency)}"
    )
    code, stdout, stderr = run(["bash", "-lc", script], timeout=120)
    message = (stdout.strip().splitlines()[-1:] or stderr.strip().splitlines()[-1:] or [""])[0]
    return code == 0, message, backup_schedule_status()


def create_backup() -> tuple[bool, str]:
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
    code, stdout, stderr = run(["bash", "-lc", script], timeout=180)
    text = (stdout.strip().splitlines()[-1:] or stderr.strip().splitlines()[-1:] or [""])[0]
    return code == 0, text


def safe_backup_path(name: str) -> Path:
    raw = str(name or "").strip()
    if not raw or raw != os.path.basename(raw) or not BACKUP_NAME_RE.match(raw) or raw.endswith(".sha256"):
        raise ValueError("invalid backup name")
    candidate = (BACKUP_DIR / raw).resolve()
    base = BACKUP_DIR.resolve()
    if base != candidate.parent:
        raise ValueError("invalid backup path")
    if not candidate.exists():
        raise FileNotFoundError("backup not found")
    return candidate


def launch_restore_backup(name: str, password: str = "") -> dict[str, Any]:
    backup_path = safe_backup_path(name)
    if backup_path.name.endswith(".enc") and not password:
        raise ValueError("password required for encrypted backup")
    BACKUP_RESTORE_LOG.parent.mkdir(parents=True, exist_ok=True)
    quoted_path = shlex.quote(str(backup_path))
    quoted_password = shlex.quote(password)
    quoted_log = shlex.quote(str(BACKUP_RESTORE_LOG))
    script = (
        "sleep 1; "
        "source /opt/pcatelegram_web/lib/common.sh; "
        "source /opt/pcatelegram_web/lib/i18n.sh; "
        "source /opt/pcatelegram_web/lib/telemt.sh; "
        "source /opt/pcatelegram_web/lib/website.sh; "
        "source /opt/pcatelegram_web/lib/backup.sh; "
        "load_language \"$(detect_language 2>/dev/null || echo en)\"; "
        "create_backup \"\" >/dev/null 2>&1 || true; "
        f"restore_backup {quoted_path} {quoted_password} yes; "
        "cleanup_old_backups 30"
    )
    with BACKUP_RESTORE_LOG.open("ab") as log:
        log.write(f"\n[{utc_now()}] restore requested for {backup_path.name}\n".encode("utf-8"))
        subprocess.Popen(
            ["bash", "-lc", f"{script} >> {quoted_log} 2>&1"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return {"name": backup_path.name, "started": True, "log": str(BACKUP_RESTORE_LOG)}


def user_qr_png(name: str) -> tuple[bytes, str]:
    users = read_user_records()
    record = users.get(name)
    if not record:
        raise FileNotFoundError("user not found")
    link = proxy_link(str(record.get("secret", "")))
    code, image, error = run_bytes(["qrencode", "-t", "PNG", "-s", "8", "-m", "2", "-o", "-", link], timeout=8)
    if code != 0 or not image:
        raise RuntimeError(error.strip() or "qrencode is not installed")
    return image, link


def read_log_payload(service: str) -> dict[str, Any]:
    allowed = {"telemt", "nginx", "mita", "pcatelegram_web-bot", "pcatelegram_web-stats", "pcatelegram_web-admin"}
    if service not in allowed:
        raise ValueError("unsupported service")
    code, stdout, stderr = run(["journalctl", "-u", service, "-n", "180", "--no-pager", "-o", "short-iso"], timeout=10)
    text = stdout if code == 0 else stderr
    lines = text.splitlines()
    if code == 0 and not lines:
        text = f"No journal entries for {service}."
        lines = [text]
    return {
        "service": service,
        "ok": code == 0,
        "exit_code": code,
        "line_count": len(lines),
        "text": text,
    }


def user_payload(
    name: str,
    secret: str,
    enabled: bool = True,
    max_unique_ips: int = 0,
    include_runtime: bool = False,
    traffic_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "name": name,
        "secret": secret,
        "link": proxy_link(secret),
        "main": name == "main",
        "enabled": bool(enabled),
        "max_unique_ips": _int_value(max_unique_ips),
        "warp": user_warp_payload(name),
    }
    if traffic_snapshot:
        item["traffic"] = {
            "epoch": traffic_snapshot.get("epoch", 0),
            "total_octets": traffic_snapshot.get("total_octets", 0),
            "current_connections": traffic_snapshot.get("current_connections", 0),
            "active_unique_ips": traffic_snapshot.get("active_unique_ips", 0),
            "recent_unique_ips": traffic_snapshot.get("recent_unique_ips", 0),
        }
    if include_runtime and enabled:
        item["runtime"] = telemt_api(f"/v1/users/{urllib.parse.quote(name, safe='')}")
    return item


def overview_payload() -> dict[str, Any]:
    config = load_json(PCATELEGRAM_WEB_CONFIG, {}) or {}
    language = read_language(config)
    users = read_user_records()
    current = load_json(CURRENT_STATS, {}) or {}
    history = load_stats_history()
    summary = telemt_api("/v1/stats/summary")
    services = {
        "telemt": service_status("telemt"),
        "mieru": service_status("mita"),
        "nginx": service_status("nginx"),
        "bot": service_status("pcatelegram_web-bot"),
        "stats": service_status("pcatelegram_web-stats"),
        "admin": service_status("pcatelegram_web-admin"),
    }
    return {
        "version": VERSION,
        "time": utc_now(),
        "language": language,
        "admin_bind": {"host": HOST, "port": PORT},
        "config": public_config(config),
        "site_status": site_status(config),
        "site_mask": site_mask_status(),
        "users_count": len(users),
        "services": services,
        "port_map": port_status(int(config.get("port") or read_telemt_port() or 443)),
        "port_443": port_443_status(),
        "stats_current": current,
        "stats_history": history,
        "stats_status": stats_status(current, history),
        "runtime_summary": summary,
        "backups": list_backups(),
        "backup_schedule": backup_schedule_status(),
        "warp": public_warp_config(),
        "mieru": public_mieru_config(),
        "routing": routing_payload(),
    }


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "PCAtelegram_webProAdmin/2.5.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def cookie_session(self) -> str:
        raw = self.headers.get("Cookie", "")
        for item in raw.split(";"):
            item = item.strip()
            if item.startswith(SESSION_COOKIE + "="):
                return item.split("=", 1)[1]
        return ""

    def is_authorized(self) -> bool:
        return session_is_valid(self.cookie_session())

    def require_auth(self) -> bool:
        if self.is_authorized():
            return True
        self.send_error_json(401, "unauthorized")
        return False

    def is_https_request(self) -> bool:
        return (
            self.headers.get("X-Forwarded-Proto", "").lower() == "https"
            or self.headers.get("X-Forwarded-Ssl", "").lower() == "on"
        )

    def send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )

    def send_login_page(self) -> None:
        body = login_page()
        self.send_response(200)
        self.send_security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def set_session_cookie(self, token: str) -> None:
        secure = "; Secure" if self.is_https_request() else ""
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax{secure}; Max-Age={SESSION_TTL_SECONDS}",
        )

    def clear_session_cookie(self) -> None:
        secure = "; Secure" if self.is_https_request() else ""
        self.send_header("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax{secure}; Max-Age=0")

    def credentials_match(self, username: str, password: str) -> bool:
        expected_user, expected_password = load_admin_credentials()
        return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_password)

    def handle_login(self) -> None:
        try:
            body = self.read_json_body()
        except Exception:
            self.send_error_json(400, "bad request")
            return
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", ""))
        if not self.credentials_match(username, password):
            self.send_error_json(401, "invalid credentials")
            return
        token = make_session()
        payload = json.dumps({"ok": True, "data": {"user": username}}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.set_session_cookie(token)
        self.send_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_logout(self) -> None:
        clear_session(self.cookie_session())
        body = b'{"ok": true}\n'
        self.send_response(200)
        self.clear_session_cookie()
        self.send_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_mieru_subscription(self, parsed: urllib.parse.ParseResult) -> None:
        match = re.fullmatch(r"/sub/mieru/([A-Za-z0-9_-]+)\.yaml", parsed.path)
        if not match:
            self.send_error(404)
            return
        cfg = read_mieru_config()
        token = str(cfg.get("subscription_token") or "")
        if not token or not hmac.compare_digest(match.group(1), token) or not cfg.get("password"):
            self.send_error(404)
            return
        body = mieru_mihomo_proxy(cfg).encode("utf-8")
        self.send_response(200)
        self.send_security_headers()
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Disposition", 'inline; filename="pcatelegram_web_mieru.yaml"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def read_json_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1024 * 1024:
            raise ValueError("request body too large")
        if length <= 0:
            return {}
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("content-type must be application/json")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def require_write_guard(self) -> bool:
        if self.command in {"POST", "PUT", "PATCH", "DELETE"} and self.headers.get("X-PCAtelegram-Web-Admin") != "1":
            self.send_error_json(403, "missing write guard")
            return False
        return True

    def route_get_api(self, parsed: urllib.parse.ParseResult) -> None:
        path = parsed.path
        if path == "/api/overview":
            self.send_json({"ok": True, "data": overview_payload()})
        elif path == "/api/routing":
            qs = urllib.parse.parse_qs(parsed.query)
            port_raw = qs.get("port", [""])[0]
            try:
                port = normalize_port(port_raw) if port_raw else None
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            self.send_json({"ok": True, "data": routing_payload(port)})
        elif path == "/api/warp":
            self.send_json({"ok": True, "data": public_warp_config()})
        elif path == "/api/mieru":
            self.send_json({"ok": True, "data": public_mieru_config()})
        elif path == "/api/users":
            users = read_user_records()
            latest = latest_user_stats()
            items = []
            for name in sorted(users, key=lambda item: (item != "main", item)):
                record = users[name]
                items.append(user_payload(
                    name,
                    record["secret"],
                    record["enabled"],
                    record.get("max_unique_ips", 0),
                    traffic_snapshot=current_user_traffic_snapshot(name, record["enabled"], latest.get(name)),
                ))
            self.send_json({"ok": True, "data": items})
        elif path.startswith("/api/users/") and path.endswith("/qr"):
            name = urllib.parse.unquote(path[len("/api/users/"):-len("/qr")])
            try:
                png, link = user_qr_png(name)
            except FileNotFoundError:
                self.send_error_json(404, "user not found")
                return
            except Exception as exc:
                self.send_error_json(503, str(exc))
                return
            self.send_response(200)
            self.send_security_headers()
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Proxy-Link", urllib.parse.quote(link, safe=""))
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
        elif path.startswith("/api/users/") and path.endswith("/traffic"):
            name = urllib.parse.unquote(path[len("/api/users/"):-len("/traffic")])
            users = read_user_records()
            if name not in users:
                self.send_error_json(404, "user not found")
                return
            qs = urllib.parse.parse_qs(parsed.query)
            range_key = normalize_range(qs.get("range", ["1h"])[0])
            all_history = load_user_stats_history(name, limit=history_limit_for_range("month"))
            history = filter_history_by_range(all_history[-history_limit_for_range(range_key):], range_key)
            current = runtime_user_traffic(name, bool(users[name].get("enabled")))
            self.send_json({
                "ok": True,
                "data": {
                    "name": name,
                    "range": range_key,
                    "current": current,
                    "history": history,
                    "summary_rows": user_traffic_interval_summaries(all_history),
                    "status": {
                        "history_exists": USER_HISTORY_FILE.exists(),
                        "history_rows": count_user_history_rows(name),
                        "history_points": len(history),
                        "last_ts": history[-1]["epoch"] if history else 0,
                        "runtime_ok": current.get("ok", False),
                    },
                },
            })
        elif path.startswith("/api/users/"):
            name = urllib.parse.unquote(path[len("/api/users/"):])
            users = read_user_records()
            if name not in users:
                self.send_error_json(404, "user not found")
                return
            record = users[name]
            self.send_json({"ok": True, "data": user_payload(
                name,
                record["secret"],
                record["enabled"],
                record.get("max_unique_ips", 0),
                include_runtime=True,
                traffic_snapshot=current_user_traffic_snapshot(name, record["enabled"], latest_user_stats().get(name)),
            )})
        elif path == "/api/backups":
            self.send_json({"ok": True, "data": list_backups()})
        elif path == "/api/backups/schedule":
            self.send_json({"ok": True, "data": backup_schedule_status()})
        elif path == "/api/stats":
            qs = urllib.parse.parse_qs(parsed.query)
            range_key = normalize_range(qs.get("range", ["1h"])[0])
            current = load_json(CURRENT_STATS, {}) or {}
            all_history = load_stats_history(limit=history_limit_for_range("month"))
            history = filter_history_by_range(all_history[-history_limit_for_range(range_key):], range_key)
            self.send_json({
                "ok": True,
                "data": {
                    "range": range_key,
                    "current": current,
                    "history": history,
                    "summary_rows": traffic_interval_summaries(all_history),
                    "status": stats_status(current, history),
                },
            })
        elif path == "/api/site/check":
            self.send_json({"ok": True, "data": site_status()})
        elif path == "/api/site/mask":
            self.send_json({"ok": True, "data": site_mask_status()})
        elif path == "/api/logs":
            qs = urllib.parse.parse_qs(parsed.query)
            service = qs.get("service", ["telemt"])[0]
            try:
                payload = read_log_payload(service)
            except ValueError:
                self.send_error_json(400, "unsupported service")
                return
            self.send_json({"ok": True, "data": payload})
        else:
            self.send_error_json(404, "not found")

    def route_post_api(self, parsed: urllib.parse.ParseResult) -> None:
        if not self.require_write_guard():
            return
        path = parsed.path
        try:
            body = self.read_json_body()
        except Exception as exc:
            self.send_error_json(400, str(exc))
            return

        if path == "/api/users":
            name = str(body.get("name", "")).strip()
            if not USER_RE.match(name):
                self.send_error_json(400, "invalid user name")
                return
            try:
                with FileLock(USER_LOCK_FILE):
                    records = read_user_records()
                    if name in records:
                        self.send_error_json(409, "user already exists")
                        return
                    users = read_telemt_users()
                    seed = f"{name}:{time.time()}:{secrets.token_hex(32)}".encode()
                    secret = hashlib.sha256(seed).hexdigest()[:32]
                    users[name] = secret
                    write_telemt_users(users)
            except Exception as exc:
                self.send_error_json(500, f"failed to save config: {exc}")
                return
            restart_requested = request_service_restart("telemt")
            self.send_json({"ok": True, "data": user_payload(name, secret, True, 0), "restart": {"mode": "async", "requested": restart_requested}})
        elif path == "/api/routing":
            try:
                port = normalize_port(body.get("port"))
                mask_host = normalize_mask_host(body.get("mask_host"))
                payload = write_routing_settings(port, mask_host)
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            except RuntimeError as exc:
                self.send_error_json(409, str(exc))
                return
            except Exception as exc:
                self.send_error_json(500, f"failed to save routing: {exc}")
                return
            self.send_json({"ok": True, "data": payload})
        elif path == "/api/site/mask":
            action = str(body.get("action") or "install").strip().lower()
            domain = str(body.get("domain") or "").strip().lower()
            html = str(body.get("html") or "")
            try:
                if action in {"install", "upload"}:
                    payload = install_mask_site(domain, html)
                elif action == "remove":
                    payload = remove_mask_site()
                else:
                    self.send_error_json(400, "unsupported site action")
                    return
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            except RuntimeError as exc:
                self.send_error_json(409, str(exc))
                return
            except Exception as exc:
                self.send_error_json(500, f"failed to manage site: {exc}")
                return
            self.send_json({"ok": True, "data": payload})
        elif path.startswith("/api/users/") and path.endswith("/max-ips"):
            name = urllib.parse.unquote(path[len("/api/users/"):-len("/max-ips")])
            try:
                limit = normalize_max_unique_ips(body.get("max_unique_ips"))
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            try:
                with FileLock(USER_LOCK_FILE):
                    records = read_user_records()
                    if name not in records:
                        self.send_error_json(404, "user not found")
                        return
                    limits = read_user_max_unique_ips()
                    if limit > 0:
                        limits[name] = limit
                    else:
                        limits.pop(name, None)
                    write_user_max_unique_ips(limits)
                    record = read_user_records()[name]
            except Exception as exc:
                self.send_error_json(500, f"failed to save config: {exc}")
                return
            restart_requested = request_service_restart("telemt")
            self.send_json({"ok": True, "data": user_payload(
                name,
                record["secret"],
                record["enabled"],
                record.get("max_unique_ips", 0),
                traffic_snapshot=current_user_traffic_snapshot(name, record["enabled"], latest_user_stats().get(name)),
            ), "restart": {"mode": "async", "requested": restart_requested}})
        elif path.startswith("/api/users/") and path.endswith("/enabled"):
            name = urllib.parse.unquote(path[len("/api/users/"):-len("/enabled")])
            enabled = bool(body.get("enabled"))
            try:
                with FileLock(USER_LOCK_FILE):
                    active = read_telemt_users()
                    disabled = read_disabled_users()
                    records = read_user_records()
                    if name not in records:
                        self.send_error_json(404, "user not found")
                        return
                    if enabled:
                        secret = disabled.pop(name, records[name]["secret"])
                        active[name] = secret
                    else:
                        secret = active.pop(name, records[name]["secret"])
                        disabled[name] = secret
                    if enabled:
                        write_telemt_users(active)
                        write_disabled_users(disabled)
                    else:
                        write_disabled_users(disabled)
                        write_telemt_users(active)
            except Exception as exc:
                self.send_error_json(500, f"failed to save config: {exc}")
                return
            restart_requested = request_service_restart("telemt")
            self.send_json({"ok": True, "data": user_payload(
                name,
                secret,
                enabled,
                records[name].get("max_unique_ips", 0),
                traffic_snapshot=current_user_traffic_snapshot(name, enabled, latest_user_stats().get(name)),
            ), "restart": {"mode": "async", "requested": restart_requested}})
        elif path == "/api/backups":
            ok, result = create_backup()
            self.send_json({"ok": ok, "data": {"path": result, "backups": list_backups()}}, 200 if ok else 500)
        elif path == "/api/backups/schedule":
            try:
                frequency = str(body.get("frequency") or "off").strip().lower()
                ok, message, status = set_backup_schedule(frequency)
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            self.send_json({"ok": ok, "data": {"message": message, "schedule": status}}, 200 if ok else 500)
        elif path == "/api/backups/restore":
            try:
                payload = launch_restore_backup(str(body.get("name") or ""), str(body.get("password") or ""))
            except FileNotFoundError:
                self.send_error_json(404, "backup not found")
                return
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            except Exception as exc:
                self.send_error_json(500, str(exc))
                return
            self.send_json({"ok": True, "data": payload}, 202)
        elif path == "/api/stats/collect":
            ok, message, payload = run_stats_action("collect")
            payload["message"] = message
            self.send_json({"ok": ok, "data": payload}, 200 if ok else 500)
        elif path == "/api/stats/repair":
            ok, message, payload = run_stats_action("repair")
            payload["message"] = message
            self.send_json({"ok": ok, "data": payload}, 200 if ok else 500)
        elif path == "/api/settings/language":
            try:
                lang_payload = write_language(str(body.get("language", "")))
            except Exception as exc:
                self.send_error_json(400, str(exc))
                return
            self.send_json({"ok": True, "data": lang_payload})
        elif path == "/api/settings/auth":
            current_password = str(body.get("current_password", ""))
            username = str(body.get("username", "")).strip()
            new_password = str(body.get("new_password", ""))
            current_user, current_expected = load_admin_credentials()
            if not hmac.compare_digest(current_password, current_expected):
                self.send_error_json(403, "current password is wrong")
                return
            if not USER_RE.match(username):
                self.send_error_json(400, "invalid username")
                return
            if len(new_password) < 4:
                self.send_error_json(400, "password must be at least 4 chars")
                return
            try:
                write_admin_credentials(username, new_password)
            except Exception as exc:
                self.send_error_json(500, f"failed to save credentials: {exc}")
                return
            self.send_json({"ok": True, "data": {"user": username, "changed": username != current_user or new_password != current_expected}})
        elif path == "/api/warp":
            current = read_warp_config()
            mode = str(body.get("mode") or "off").strip().lower()
            if mode not in {"off", "warp", "warp_plus"}:
                self.send_error_json(400, "invalid WARP mode")
                return
            scope = str(body.get("scope") or "all").strip().lower()
            if scope not in {"all", "user"}:
                self.send_error_json(400, "invalid WARP scope")
                return
            user = str(body.get("user") or "").strip()
            if scope == "user":
                records = read_user_records()
                if not USER_RE.match(user) or user not in records:
                    self.send_error_json(400, "invalid WARP user")
                    return
            else:
                user = ""
            license_key = str(body.get("license_key") or "").strip()
            if not license_key:
                if scope == "user" and user:
                    license_key = str(current.get("users", {}).get(user, {}).get("license_key", ""))
                else:
                    license_key = str(current.get("license_key", ""))
            enabled = mode != "off"
            next_cfg = dict(current)
            next_cfg.update({
                "enabled": enabled,
                "mode": mode,
                "scope": scope,
                "user": user,
            })
            if scope == "all":
                next_cfg["license_key"] = license_key
            else:
                users_cfg = dict(next_cfg.get("users") or {})
                users_cfg[user] = {
                    "mode": mode,
                    "license_key": license_key,
                    "updated_at": utc_now(),
                }
                next_cfg["users"] = users_cfg
            try:
                write_warp_config(next_cfg)
                apply_result = apply_warp_runtime(next_cfg)
            except Exception as exc:
                self.send_error_json(500, f"failed to save WARP config: {exc}")
                return
            self.send_json({"ok": True, "data": {"config": public_warp_config(), "apply": apply_result}})
        elif path == "/api/mieru":
            action = str(body.get("action") or "install").strip().lower()
            try:
                if action in {"install", "save"}:
                    payload = save_mieru_settings(body)
                else:
                    payload = control_mieru(action)
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            except RuntimeError as exc:
                self.send_error_json(409, str(exc))
                return
            except Exception as exc:
                self.send_error_json(500, f"failed to manage Mieru: {exc}")
                return
            self.send_json({"ok": True, "data": payload})
        elif path == "/api/auth/logout":
            self.handle_logout()
        elif path.startswith("/api/services/") and path.endswith("/restart"):
            service = path[len("/api/services/"):-len("/restart")]
            allowed = {"telemt", "nginx", "mita", "pcatelegram_web-bot", "pcatelegram_web-stats"}
            if service not in allowed:
                self.send_error_json(400, "unsupported service")
                return
            ok = restart_service(service)
            self.send_json({"ok": ok, "status": service_status(service)}, 200 if ok else 500)
        else:
            self.send_error_json(404, "not found")

    def route_delete_api(self, parsed: urllib.parse.ParseResult) -> None:
        if not self.require_write_guard():
            return
        path = parsed.path
        if not path.startswith("/api/users/"):
            self.send_error_json(404, "not found")
            return
        name = urllib.parse.unquote(path[len("/api/users/"):])
        if name == "main":
            self.send_error_json(400, "main user cannot be deleted")
            return
        try:
            with FileLock(USER_LOCK_FILE):
                active = read_telemt_users()
                disabled = read_disabled_users()
                records = read_user_records()
                if name not in records:
                    self.send_error_json(404, "user not found")
                    return
                active.pop(name, None)
                disabled.pop(name, None)
                limits = read_user_max_unique_ips()
                limits.pop(name, None)
                warp_cfg = read_warp_config()
                warp_users = dict(warp_cfg.get("users") or {})
                warp_users.pop(name, None)
                warp_cfg["users"] = warp_users
                if warp_cfg.get("user") == name:
                    warp_cfg["enabled"] = False
                    warp_cfg["mode"] = "off"
                    warp_cfg["user"] = ""
                write_telemt_users(active)
                write_disabled_users(disabled)
                write_user_max_unique_ips(limits)
                write_warp_config(warp_cfg)
        except Exception as exc:
            self.send_error_json(500, f"failed to save config: {exc}")
            return
        restart_requested = request_service_restart("telemt")
        self.send_json({"ok": True, "restart": {"mode": "async", "requested": restart_requested}})

    def send_static(self, parsed: urllib.parse.ParseResult) -> None:
        rel = parsed.path.lstrip("/") or "index.html"
        if rel.startswith("api/") or ".." in rel.split("/"):
            self.send_error(404)
            return
        path = STATIC_DIR / rel
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            path = STATIC_DIR / "index.html"
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404)
            return
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_security_headers()
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/sub/mieru/"):
            self.send_mieru_subscription(parsed)
            return
        if not self.is_authorized():
            if parsed.path.startswith("/api/"):
                self.send_error_json(401, "unauthorized")
            else:
                self.send_login_page()
            return
        if parsed.path.startswith("/api/"):
            self.route_get_api(parsed)
        else:
            self.send_static(parsed)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/auth/login":
            self.handle_login()
            return
        if not self.require_auth():
            return
        if parsed.path.startswith("/api/"):
            self.route_post_api(parsed)
        else:
            self.send_error(404)

    def do_DELETE(self) -> None:
        if not self.require_auth():
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.route_delete_api(parsed)
        else:
            self.send_error(404)


def main() -> None:
    if not STATIC_DIR.exists():
        raise SystemExit(f"static dir not found: {STATIC_DIR}")
    httpd = ThreadingHTTPServer((HOST, PORT), AdminHandler)
    print(f"PCAtelegram_web admin listening on http://{HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
