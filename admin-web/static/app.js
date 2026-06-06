const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const i18n = {
  en: {
    brandSubtitle: "Local Admin",
    navDashboard: "Dashboard",
    navTraffic: "Traffic",
    navKeys: "Keys",
    navBackups: "Backups",
    navLogs: "Logs",
    navSettings: "Settings",
    refresh: "Refresh",
    autoRefresh: "Auto refresh every 5 seconds",
    autoRefreshOn: "Auto refresh is on",
    autoRefreshOff: "Auto refresh is off",
    autoRefreshOffShort: "off",
    themeDark: "Dark",
    themeLight: "Light",
    metricMode: "Mode",
    metricKeys: "Keys",
    metricProxyTraffic: "Proxy traffic",
    metricSiteTraffic: "Site traffic",
    configuredUsers: "configured users",
    packets: "packets",
    servicesEyebrow: "Services",
    servicesTitle: "Service health",
    servicesHelp: "Systemd service status for telemt, nginx, the bot, the traffic collector and the local admin.",
    runtimeEyebrow: "Runtime",
    runtimeTitle: "telemt summary",
    runtimeHelp: "Runtime data comes from the local telemt API and shows what the proxy engine sees right now.",
    trafficEyebrow: "Traffic",
    trafficTitle: "History",
    keysEyebrow: "Access",
    keysTitle: "User keys",
    backupsEyebrow: "Snapshots",
    backupsTitle: "Backups",
    eventsEyebrow: "Events",
    eventsTitle: "Activity",
    logsEyebrow: "Journal",
    logsTitle: "Logs",
    settingsEyebrow: "Settings",
    settingsTitle: "Panel preferences",
    configEyebrow: "Config",
    configTitle: "Installation state",
    collector: "Collector",
    lastPoint: "Last point",
    historyRows: "History rows",
    collectStats: "Update stats",
    collectStatsHelp: "Run one traffic collection now.",
    repairStats: "Restart collector",
    repairStatsHelp: "Reinstall and restart the background service that writes traffic history.",
    tableTime: "Time",
    tablePeriod: "Period",
    tableStatus: "Status",
    tableProxyDelta: "Proxy delta",
    tableSiteDelta: "Site delta",
    tableProxyTotal: "Proxy total",
    tableSiteTotal: "Site total",
    tableUser: "User",
    tableSecret: "Secret",
    tableLink: "Link",
    tableTraffic: "Traffic",
    ipLimit: "IP limit",
    ipLimitHint: "0 = unlimited",
    saveIpLimit: "OK",
    tableTrafficDelta: "Traffic delta",
    tableTrafficTotal: "Total",
    tableActions: "Actions",
    userPlaceholder: "client-name",
    addKey: "Add key",
    copyLink: "Copy link",
    copySecret: "Copy secret",
    showQr: "QR",
    delete: "Delete",
    enabled: "Enabled",
    disabled: "Disabled",
    applying: "Applying...",
    changesApplyInBackground: "Changes are being applied in the background",
    disableKey: "Disable key",
    enableKey: "Enable key",
    main: "main",
    createBackup: "Create backup",
    restoreBackup: "Restore",
    encryptedRestoreCli: "Encrypted backups are restored from CLI",
    backupScheduleTitle: "Automatic backups",
    backupScheduleLoading: "Loading schedule...",
    backupIncludesTitle: "Backup contents",
    backupIncludesText: "telemt config, PCAtelegram_web settings, keys, disabled keys, site, templates, SSL certificates, bot, admin panel and traffic history.",
    scheduleOff: "Off",
    scheduleDaily: "Daily",
    scheduleWeekly: "Weekly",
    scheduleMonthly: "Monthly",
    scheduleSaved: "Schedule saved",
    scheduleNext: "Next run: {value}",
    scheduleDisabled: "Automatic backups are disabled",
    backupRestoreStarted: "Restore started",
    confirmRestoreBackup: "Restore backup",
    loadLogs: "Load",
    panelLanguage: "Panel language",
    theme: "Theme",
    bindAddress: "Bind address",
    authSettingsTitle: "Login credentials",
    authCurrentPassword: "Current password",
    authUsername: "Username",
    authNewPassword: "New password",
    authSave: "Save login",
    authSaved: "Login updated",
    routingEyebrow: "Network",
    routingTitle: "Port and mask site",
    routingPort: "Public port",
    routingMaskHost: "Mask site",
    routingSave: "Save routing",
    routingSaveShort: "Save",
    routingSaved: "Routing saved",
    routingOk: "port free",
    routingBusy: "port busy",
    routingPerUserNote: "One telemt instance has one public port and one mask site for all links. Different ports per client need separate telemt services.",
    routingCurrentMask: "Mask site: {value}",
    warpEyebrow: "Routing",
    warpTitle: "WARP / WARP+",
    warpMode: "Mode",
    warpOff: "Off",
    warpScope: "Scope",
    warpAllClients: "All clients",
    warpOneClient: "One client",
    warpClient: "Client",
    warpLicense: "WARP+ key",
    warpSave: "Save WARP",
    warpSaved: "WARP settings saved",
    warpInstalled: "warp-cli installed",
    warpNotInstalled: "will install on save",
    warpPerUserNote: "One-client WARP profile is stored here. If warp-cli is missing, it will be installed on save. Runtime per-client routing needs a dedicated telemt route; global WARP applies to all clients.",
    warpAllNote: "Global WARP applies to all proxy traffic. If warp-cli is missing, it will be installed on save, then connected.",
    savedKey: "saved key",
    dashboard: "Dashboard",
    noKeys: "No keys yet",
    noBackups: "No backups yet",
    noEvents: "No events yet",
    noHistory: "No traffic history yet",
    noTrafficForRange: "No data for this range yet",
    noRuntime: "Runtime data is not available",
    userTrafficEyebrow: "Per user",
    userTrafficTitle: "User traffic",
    selectUserTraffic: "Select a key to see its traffic history",
    openStats: "Stats",
    trafficTotal: "Total",
    currentConnections: "Connections",
    activeIps: "Active IPs",
    recentIps: "Recent IPs",
    trafficRuntimeUnavailable: "Runtime unavailable",
    badConnections: "Bad connections",
    connections: "Connections",
    uptime: "Uptime",
    users: "Users",
    revision: "Revision",
    healthOk: "OK",
    healthError: "Error",
    healthStale: "Stale",
    healthStopped: "Stopped",
    healthNotInstalled: "Not installed",
    healthUnknown: "Unknown",
    statusRunning: "running",
    statusInactive: "inactive",
    statusStopped: "stopped",
    statusFailed: "failed",
    statusNotInstalled: "not installed",
    statusActivating: "activating",
    statusDeactivating: "deactivating",
    statusUnknown: "unknown",
    statsMissing: "Collector is not running",
    statsOk: "Collector is running",
    statsStale: "Snapshot is stale",
    statsError: "Collector error",
    restart: "Restart",
    copied: "Copied",
    copyFailed: "Copy failed",
    keyCreated: "Key created",
    keyDeleted: "Key deleted",
    backupCreated: "Backup created",
    qrUnavailable: "QR code is unavailable",
    serviceRestarted: "Service restarted",
    statsRepaired: "Collector restarted",
    statsCollected: "Statistics collected",
    confirmDelete: "Delete key",
    confirmRestart: "Restart",
    invalidUser: "Use latin letters, digits, _, . or -",
    loading: "Loading...",
    never: "never",
    lightTheme: "Light",
    darkTheme: "Dark",
    configMode: "Mode",
    configDomain: "Domain",
    configSiteStatus: "Site check",
    configTemplate: "Template",
    configVersion: "Version",
    siteOk: "Site 200 OK",
    siteHttp: "Site HTTP",
    siteMissing: "Domain is not configured",
    siteInvalid: "Invalid domain",
    siteError: "Site check failed",
    siteNotChecked: "Site check pending",
    logsLines: "lines",
    logsNoData: "No log lines",
    languageSaved: "Language saved",
    keyEnabled: "Key enabled",
    keyDisabled: "Key disabled",
    ipLimitSaved: "IP limit saved",
    visualTitle: "Port {port} map",
    visualText: "Shows the selected public listener. Port 443 may be occupied by Xray / 3x-ui; busy ports are blocked on save.",
    port443Checked: "checked",
    port443NoListeners: "No 443 listeners found",
    port443Listeners: "listeners",
    port443Routes: "routed",
    port443Error: "Port check failed",
    port443Public: "public",
    port443Configured: "telemt: {port}",
    port443PublicSection: "Public port {port}",
    port443BehindSection: "Behind port {port}",
    port443NoRoutes: "No routed services detected",
    port443Via: "via {value}",
    roleMtproxy: "MTProxy",
    roleEdge: "443 Edge",
    roleSite: "Website",
    roleXray: "Xray / 3x-ui",
    roleAmneziawg: "AmneziaWG",
    roleOther: "Other",
    range15m: "15 min",
    range1h: "1 hour",
    range24h: "24 hours",
    rangeMonth: "Month",
    viewChart: "Chart",
    viewRows: "Rows",
    chartMax: "max {value} per interval",
    chartProxy: "proxy",
    chartSite: "site",
    encrypted: "encrypted",
    ariaAdminSections: "Admin sections",
    ariaMenu: "Open menu",
    ariaLanguage: "Language",
    ariaClose: "Close",
    ariaTrafficHistory: "Traffic history",
    ariaTrafficRange: "Traffic range",
    ariaTrafficView: "Traffic view",
    qrEyebrow: "QR import",
    qrTitle: "Scan Telegram proxy",
    pageDashboardTitle: "Dashboard",
    pageDashboardKicker: "Local Admin",
    pageTrafficTitle: "Traffic",
    pageTrafficKicker: "Statistics",
    pageKeysTitle: "Keys",
    pageKeysKicker: "Access",
    pageBackupsTitle: "Backups",
    pageBackupsKicker: "Migration",
    pageLogsTitle: "Logs",
    pageLogsKicker: "Journal",
    pageSettingsTitle: "Settings",
    pageSettingsKicker: "Preferences",
  },
  ru: {
    brandSubtitle: "Локальная админка",
    navDashboard: "Обзор",
    navTraffic: "Трафик",
    navKeys: "Ключи",
    navBackups: "Бекапы",
    navLogs: "Логи",
    navSettings: "Настройки",
    refresh: "Обновить",
    autoRefresh: "Автообновление каждые 5 секунд",
    autoRefreshOn: "Автообновление включено",
    autoRefreshOff: "Автообновление выключено",
    autoRefreshOffShort: "выкл",
    themeDark: "Тёмная",
    themeLight: "Светлая",
    metricMode: "Режим",
    metricKeys: "Ключи",
    metricProxyTraffic: "Трафик прокси",
    metricSiteTraffic: "Трафик сайта",
    configuredUsers: "настроенных пользователей",
    packets: "пакетов",
    servicesEyebrow: "Сервисы",
    servicesTitle: "Состояние служб",
    servicesHelp: "Статус systemd-служб: telemt, nginx, бот, сборщик трафика и локальная админка.",
    runtimeEyebrow: "Среда выполнения",
    runtimeTitle: "Сводка telemt",
    runtimeHelp: "Данные среды выполнения берутся из локального API telemt и показывают, что ядро прокси видит прямо сейчас.",
    trafficEyebrow: "Трафик",
    trafficTitle: "История",
    keysEyebrow: "Доступ",
    keysTitle: "Ключи пользователей",
    backupsEyebrow: "Снимки",
    backupsTitle: "Бекапы",
    eventsEyebrow: "События",
    eventsTitle: "Активность",
    logsEyebrow: "Журнал",
    logsTitle: "Логи",
    settingsEyebrow: "Настройки",
    settingsTitle: "Параметры панели",
    configEyebrow: "Конфиг",
    configTitle: "Состояние установки",
    collector: "Сборщик",
    lastPoint: "Последняя точка",
    historyRows: "Строк истории",
    collectStats: "Обновить статистику",
    collectStatsHelp: "Запустить один сбор трафика прямо сейчас.",
    repairStats: "Перезапустить сборщик",
    repairStatsHelp: "Переустановить и перезапустить фоновую службу, которая пишет историю трафика.",
    tableTime: "Время",
    tablePeriod: "Период",
    tableStatus: "Статус",
    tableProxyDelta: "Прирост прокси",
    tableSiteDelta: "Прирост сайта",
    tableProxyTotal: "Всего прокси",
    tableSiteTotal: "Всего по сайту",
    tableUser: "Пользователь",
    tableSecret: "Секрет",
    tableLink: "Ссылка",
    tableTraffic: "Трафик",
    ipLimit: "Лимит IP",
    ipLimitHint: "0 = безлимит",
    saveIpLimit: "OK",
    tableTrafficDelta: "Прирост трафика",
    tableTrafficTotal: "Всего",
    tableActions: "Действия",
    userPlaceholder: "client-name",
    addKey: "Добавить ключ",
    copyLink: "Копировать ссылку",
    copySecret: "Копировать секрет",
    showQr: "QR",
    delete: "Удалить",
    enabled: "Включён",
    disabled: "Отключён",
    applying: "Применяется...",
    changesApplyInBackground: "Изменения применяются в фоне",
    disableKey: "Отключить ключ",
    enableKey: "Включить ключ",
    main: "основной",
    createBackup: "Создать бекап",
    restoreBackup: "Восстановить",
    encryptedRestoreCli: "Зашифрованные бекапы восстанавливаются через CLI",
    backupScheduleTitle: "Автобекапы",
    backupScheduleLoading: "Загрузка расписания...",
    backupIncludesTitle: "Что входит в бекап",
    backupIncludesText: "конфиг telemt, настройки PCAtelegram_web, ключи, отключённые ключи, сайт, шаблоны, SSL-сертификаты, бот, админка и история трафика.",
    scheduleOff: "Выкл",
    scheduleDaily: "Каждый день",
    scheduleWeekly: "Каждую неделю",
    scheduleMonthly: "Каждый месяц",
    scheduleSaved: "Расписание сохранено",
    scheduleNext: "Следующий запуск: {value}",
    scheduleDisabled: "Автобекапы отключены",
    backupRestoreStarted: "Восстановление запущено",
    confirmRestoreBackup: "Восстановить бекап",
    loadLogs: "Загрузить",
    panelLanguage: "Язык панели",
    theme: "Тема",
    bindAddress: "Адрес привязки",
    authSettingsTitle: "Данные входа",
    authCurrentPassword: "Текущий пароль",
    authUsername: "Логин",
    authNewPassword: "Новый пароль",
    authSave: "Сохранить вход",
    authSaved: "Данные входа обновлены",
    routingEyebrow: "Сеть",
    routingTitle: "Порт и маскировка",
    routingPort: "Публичный порт",
    routingMaskHost: "Сайт маскировки",
    routingSave: "Сохранить маршрут",
    routingSaveShort: "Сохранить",
    routingSaved: "Маршрутизация сохранена",
    routingOk: "порт свободен",
    routingBusy: "порт занят",
    routingPerUserNote: "Один telemt-инстанс имеет один публичный порт и один сайт маскировки для всех ссылок. Разные порты на клиентов требуют отдельные telemt-сервисы.",
    routingCurrentMask: "Маскировка: {value}",
    warpEyebrow: "Маршрутизация",
    warpTitle: "WARP / WARP+",
    warpMode: "Режим",
    warpOff: "Выкл",
    warpScope: "Область",
    warpAllClients: "Все клиенты",
    warpOneClient: "Один клиент",
    warpClient: "Клиент",
    warpLicense: "Ключ WARP+",
    warpSave: "Сохранить WARP",
    warpSaved: "Настройки WARP сохранены",
    warpInstalled: "warp-cli установлен",
    warpNotInstalled: "установится при сохранении",
    warpPerUserNote: "Профиль WARP для одного клиента сохраняется здесь. Если warp-cli нет, он установится при сохранении. Runtime-маршрут на одного клиента требует отдельный маршрут telemt; global WARP действует на всех клиентов.",
    warpAllNote: "Global WARP применится ко всему proxy-трафику. Если warp-cli нет, он установится при сохранении и затем подключится.",
    savedKey: "ключ сохранён",
    dashboard: "Обзор",
    noKeys: "Ключей пока нет",
    noBackups: "Бекапов пока нет",
    noEvents: "Событий пока нет",
    noHistory: "Истории трафика пока нет",
    noTrafficForRange: "За этот период данных пока нет",
    noRuntime: "Данные среды выполнения недоступны",
    userTrafficEyebrow: "По пользователю",
    userTrafficTitle: "Трафик ключа",
    selectUserTraffic: "Выберите ключ, чтобы увидеть историю трафика",
    openStats: "Статистика",
    trafficTotal: "Всего",
    currentConnections: "Подключения",
    activeIps: "Активные IP",
    recentIps: "Недавние IP",
    trafficRuntimeUnavailable: "Runtime недоступен",
    badConnections: "Ошибочные подключения",
    connections: "Подключения",
    uptime: "Аптайм",
    users: "Пользователи",
    revision: "Ревизия",
    healthOk: "OK",
    healthError: "Ошибка",
    healthStale: "Устарело",
    healthStopped: "Остановлено",
    healthNotInstalled: "Не установлен",
    healthUnknown: "Неизвестно",
    statusRunning: "работает",
    statusInactive: "неактивен",
    statusStopped: "остановлен",
    statusFailed: "ошибка",
    statusNotInstalled: "не установлен",
    statusActivating: "запускается",
    statusDeactivating: "останавливается",
    statusUnknown: "неизвестно",
    statsMissing: "Сборщик не запущен",
    statsOk: "Сборщик работает",
    statsStale: "Снимок устарел",
    statsError: "Ошибка сборщика",
    restart: "Перезапустить",
    copied: "Скопировано",
    copyFailed: "Не удалось скопировать",
    keyCreated: "Ключ создан",
    keyDeleted: "Ключ удалён",
    backupCreated: "Бекап создан",
    qrUnavailable: "QR-код недоступен",
    serviceRestarted: "Сервис перезапущен",
    statsRepaired: "Сборщик перезапущен",
    statsCollected: "Статистика собрана",
    confirmDelete: "Удалить ключ",
    confirmRestart: "Перезапустить",
    invalidUser: "Используйте латиницу, цифры, _, . или -",
    loading: "Загрузка...",
    never: "никогда",
    lightTheme: "Светлая",
    darkTheme: "Тёмная",
    configMode: "Режим",
    configDomain: "Домен",
    configSiteStatus: "Проверка сайта",
    configTemplate: "Шаблон",
    configVersion: "Версия",
    siteOk: "Сайт 200 OK",
    siteHttp: "Сайт HTTP",
    siteMissing: "Домен не настроен",
    siteInvalid: "Некорректный домен",
    siteError: "Проверка сайта не прошла",
    siteNotChecked: "Проверка сайта ожидает",
    logsLines: "строк",
    logsNoData: "Строк логов нет",
    languageSaved: "Язык сохранён",
    keyEnabled: "Ключ включён",
    keyDisabled: "Ключ отключён",
    ipLimitSaved: "Лимит IP сохранён",
    visualTitle: "Карта порта {port}",
    visualText: "Показывает выбранный публичный порт. 443 может быть занят Xray / 3x-ui; занятые порты блокируются при сохранении.",
    port443Checked: "проверено",
    port443NoListeners: "Слушателей 443 не найдено",
    port443Listeners: "слушателей",
    port443Routes: "за 443",
    port443Error: "Проверка порта не удалась",
    port443Public: "публичный",
    port443Configured: "telemt: {port}",
    port443PublicSection: "Публичный порт {port}",
    port443BehindSection: "За портом {port}",
    port443NoRoutes: "Маршрутизируемых сервисов не найдено",
    port443Via: "через {value}",
    roleMtproxy: "MTProxy",
    roleEdge: "443 Edge",
    roleSite: "Сайт",
    roleXray: "Xray / 3x-ui",
    roleAmneziawg: "AmneziaWG",
    roleOther: "Другое",
    range15m: "15 мин",
    range1h: "1 час",
    range24h: "24 часа",
    rangeMonth: "Месяц",
    viewChart: "График",
    viewRows: "Строки",
    chartMax: "макс. {value} за интервал",
    chartProxy: "прокси",
    chartSite: "сайт",
    encrypted: "зашифровано",
    ariaAdminSections: "Разделы админки",
    ariaMenu: "Открыть меню",
    ariaLanguage: "Язык",
    ariaClose: "Закрыть",
    ariaTrafficHistory: "История трафика",
    ariaTrafficRange: "Период трафика",
    ariaTrafficView: "Вид трафика",
    qrEyebrow: "QR-импорт",
    qrTitle: "Сканирование прокси Telegram",
    pageDashboardTitle: "Обзор",
    pageDashboardKicker: "Локальная админка",
    pageTrafficTitle: "Трафик",
    pageTrafficKicker: "Статистика",
    pageKeysTitle: "Ключи",
    pageKeysKicker: "Доступ",
    pageBackupsTitle: "Бекапы",
    pageBackupsKicker: "Переезд",
    pageLogsTitle: "Логи",
    pageLogsKicker: "Журнал",
    pageSettingsTitle: "Настройки",
    pageSettingsKicker: "Параметры",
  },
};

const state = {
  overview: null,
  stats: null,
  users: [],
  events: [],
  lang: "en",
  page: "dashboard",
  theme: document.documentElement.dataset.theme || "light",
  trafficRange: "1h",
  trafficView: "chart",
  trafficLoading: false,
  userTrafficUser: "",
  userTrafficRange: "1h",
  userTrafficView: "chart",
  userTraffic: null,
  userTrafficLoading: false,
  backupSchedule: null,
  routing: null,
  routingDirty: false,
  routingPreviewMap: null,
  warp: null,
  qrLink: "",
  pendingUsers: new Set(),
  refreshingAll: false,
  autoRefreshEnabled: localStorage.getItem("pcatelegram_web-auto-refresh") !== "0",
};

const t = (key) => (i18n[state.lang] && i18n[state.lang][key]) || i18n.en[key] || key;

const trafficRanges = ["15m", "1h", "24h", "month"];
const AUTO_REFRESH_MS = 5000;
let autoRefreshTimer = null;

const fmtBytes = (value = 0) => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = Number(value) || 0;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};

const fmtDate = (epoch) => {
  if (!epoch) return t("never");
  return new Date(epoch * 1000).toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US");
};

const fmtDuration = (seconds = 0) => {
  let value = Math.max(0, Math.floor(Number(seconds) || 0));
  const days = Math.floor(value / 86400);
  value %= 86400;
  const hours = Math.floor(value / 3600);
  value %= 3600;
  const minutes = Math.floor(value / 60);
  if (days) return `${days}d ${hours}h`;
  if (hours) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#039;",
})[ch]);

const escapeAttr = (value) => escapeHtml(value).replace(/`/g, "&#096;");

const toast = (message) => {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.remove("show"), 2800);
};

const addEvent = (title, detail = "") => {
  state.events.unshift({ title, detail, time: new Date() });
  state.events = state.events.slice(0, 10);
  renderEvents();
};

function updateAutoRefreshToggle() {
  const button = $("#autoRefreshToggle");
  if (!button) return;
  button.classList.toggle("active", state.autoRefreshEnabled);
  button.setAttribute("aria-pressed", String(state.autoRefreshEnabled));
  button.title = state.autoRefreshEnabled ? t("autoRefreshOn") : t("autoRefreshOff");
  const label = button.querySelector(".auto-refresh-state");
  if (label) label.textContent = state.autoRefreshEnabled ? "5s" : t("autoRefreshOffShort");
}

function syncAutoRefreshTimer() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  if (!state.autoRefreshEnabled) return;
  autoRefreshTimer = setInterval(() => {
    refreshAll().catch((err) => toast(err.message));
  }, AUTO_REFRESH_MS);
}

function setAutoRefresh(enabled) {
  state.autoRefreshEnabled = Boolean(enabled);
  localStorage.setItem("pcatelegram_web-auto-refresh", state.autoRefreshEnabled ? "1" : "0");
  updateAutoRefreshToggle();
  syncAutoRefreshTimer();
}

async function api(path, options = {}) {
  const headers = {
    "Accept": "application/json",
    "X-PCAtelegram-Web-Admin": "1",
    ...(options.headers || {}),
  };
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch(path, { ...options, headers, credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    window.location.assign("/");
    throw new Error("unauthorized");
  }
  if (!res.ok || data.ok === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data.data ?? data;
}

function applyI18n() {
  document.documentElement.lang = state.lang;
  $$("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $$("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  $$("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
  $$("[data-i18n-aria-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAriaLabel));
  });
  $("#themeToggle").textContent = state.theme === "dark" ? t("themeLight") : t("themeDark");
  $("#languageSelect").value = state.lang;
  $("#settingsLanguage").textContent = state.lang === "ru" ? "Русский" : "English";
  $("#settingsTheme").textContent = state.theme === "dark" ? t("darkTheme") : t("lightTheme");
  const visualPort = state.routingDirty
    ? (state.routingPreviewMap?.public_port || $("#visualRoutingPort")?.value || state.routing?.port || 443)
    : (state.overview?.port_map?.public_port || state.routing?.port || 443);
  $("#visualTitle").textContent = t("visualTitle").replace("{port}", visualPort);
  $("#visualText").textContent = t("visualText");
  updateTrafficControls();
  updateUserTrafficControls();
  renderBackupSchedule();
  renderRoutingSettings();
  renderWarpSettings();
  updatePageTitle();
  updateAutoRefreshToggle();
}

function setTheme(theme) {
  state.theme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = state.theme;
  localStorage.setItem("pcatelegram_web-theme", state.theme);
  applyI18n();
  if (state.overview) renderStats();
  if (state.userTraffic) renderUserTraffic();
}

async function setLanguage(lang) {
  const previous = state.lang;
  state.lang = lang === "ru" ? "ru" : "en";
  applyI18n();
  try {
    const data = await api("/api/settings/language", {
      method: "POST",
      body: JSON.stringify({ language: state.lang }),
    });
    state.lang = data.language === "ru" ? "ru" : "en";
    applyI18n();
    toast(t("languageSaved"));
    await refreshAll();
  } catch (err) {
    state.lang = previous;
    applyI18n();
    toast(err.message);
  }
}

async function updateAuthSettings(eventObj) {
  eventObj.preventDefault();
  const form = eventObj.currentTarget;
  const btn = form.querySelector("button[type='submit']");
  const body = {
    current_password: form.current_password.value,
    username: form.username.value.trim(),
    new_password: form.new_password.value,
  };
  btn.disabled = true;
  try {
    await api("/api/settings/auth", {
      method: "POST",
      body: JSON.stringify(body),
    });
    form.current_password.value = "";
    form.new_password.value = "";
    toast(t("authSaved"));
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
  }
}

function setPage(page, push = true) {
  const next = $(`[data-page="${page}"]`) ? page : "dashboard";
  state.page = next;
  $$(".page-panel").forEach((panel) => panel.classList.toggle("active", panel.dataset.page === next));
  $$("[data-nav]").forEach((item) => item.classList.toggle("active", item.dataset.nav === next));
  $("#sidebar").classList.remove("open");
  updatePageTitle();
  if (push && location.hash !== `#${next}`) {
    history.replaceState(null, "", `#${next}`);
  }
  requestAnimationFrame(() => {
    window.scrollTo({ top: 0, behavior: push ? "smooth" : "auto" });
  });
  if (next === "traffic") {
    refreshStats().catch((err) => toast(err.message));
  } else if (next === "keys") {
    ensureUserTrafficSelection();
    renderUserTraffic();
    if (state.userTrafficUser) refreshUserTraffic().catch((err) => toast(err.message));
  }
}

function updatePageTitle() {
  const cap = state.page.charAt(0).toUpperCase() + state.page.slice(1);
  $("#pageTitle").textContent = t(`page${cap}Title`);
  $("#pageKicker").textContent = t(`page${cap}Kicker`);
}

function updateLanguageFromOverview(data) {
  const lang = String(data.language || data.config?.language || "en").toLowerCase();
  state.lang = lang === "ru" ? "ru" : "en";
  applyI18n();
}

function statusLabel(status) {
  const key = `status${String(status || "unknown").replace(/(^|_)([a-z])/g, (_, __, ch) => ch.toUpperCase())}`;
  const label = t(key);
  return label === key ? (status || t("healthUnknown")) : label;
}

function healthLabel(health) {
  const labels = {
    ok: t("healthOk"),
    error: t("healthError"),
    stale: t("healthStale"),
    stopped: t("healthStopped"),
    not_installed: t("healthNotInstalled"),
  };
  return labels[health] || t("healthUnknown");
}

function renderServices(services = {}) {
  const items = [
    { key: "telemt", label: "telemt", api: "telemt" },
    { key: "nginx", label: "nginx", api: "nginx" },
    { key: "bot", label: "bot", api: "pcatelegram_web-bot" },
    { key: "stats", label: "stats", api: "pcatelegram_web-stats" },
    { key: "admin", label: "admin", api: "pcatelegram_web-admin" },
  ];
  $("#services").innerHTML = items.map((item) => {
    const status = services[item.key] || "unknown";
    const disabled = item.key === "admin" || status === "not_installed";
    return `<article class="service status-${escapeAttr(status)}">
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <span><i></i>${escapeHtml(statusLabel(status))}</span>
      </div>
      <button class="soft" data-restart="${escapeAttr(item.api)}" ${disabled ? "disabled" : ""}>${escapeHtml(t("restart"))}</button>
    </article>`;
  }).join("");
}

function runtimeData() {
  const raw = state.overview?.runtime_summary;
  if (!raw || typeof raw !== "object") return null;
  return raw.data && typeof raw.data === "object" ? raw.data : raw;
}

function renderRuntime() {
  const data = runtimeData();
  if (!data) {
    $("#runtimeCards").innerHTML = `<div class="empty">${escapeHtml(t("noRuntime"))}</div>`;
    $("#runtimeIssues").innerHTML = "";
    return;
  }
  const revision = String(data.revision || state.overview?.runtime_summary?.revision || "--");
  const cards = [
    [t("uptime"), fmtDuration(data.uptime_seconds)],
    [t("connections"), data.connections_total ?? 0],
    [t("badConnections"), data.connections_bad_total ?? 0],
    [t("users"), data.configured_users ?? state.overview?.users_count ?? 0],
    [t("revision"), revision.slice(0, 10)],
  ];
  $("#runtimeCards").innerHTML = cards.map(([label, value]) => `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `).join("");
  const bad = Array.isArray(data.connections_bad_by_class) ? data.connections_bad_by_class : [];
  $("#runtimeIssues").innerHTML = bad.length ? bad.map((item) => `
    <div class="issue">
      <span>${escapeHtml(item.class || "unknown")}</span>
      <strong>${escapeHtml(item.total ?? 0)}</strong>
    </div>
  `).join("") : "";
}

function siteStatusText(site = {}) {
  if (!site.host) return t("siteMissing");
  if (site.error === "invalid_domain") return t("siteInvalid");
  if (site.ok) return t("siteOk");
  if (site.checked && site.http_code) return `${t("siteHttp")} ${site.http_code}`;
  if (site.error) return t("siteError");
  return t("siteNotChecked");
}

function siteStatusClass(site = {}) {
  if (site.ok) return "ok";
  if (!site.host || !site.checked) return "warn";
  return "error";
}

function renderSiteStatus() {
  const cfg = state.overview?.config || {};
  const site = state.overview?.site_status || {};
  $("#metricDomain").textContent = site.host || cfg.domain || cfg.mask_host || "--";
  const statusEl = $("#siteStatus");
  statusEl.textContent = siteStatusText(site);
  statusEl.className = `metric-status ${siteStatusClass(site)}`;
  statusEl.title = site.url || "";
}

function roleLabel(role) {
  const key = `role${String(role || "other").replace(/(^|_)([a-z])/g, (_, __, ch) => ch.toUpperCase())}`;
  const label = t(key);
  return label === key ? t("roleOther") : label;
}

function renderPortMap(payload = {}) {
  const listeners = Array.isArray(payload.listeners) ? payload.listeners : [];
  const routes = Array.isArray(payload.routes) ? payload.routes : [];
  const summary = $("#port443Summary");
  const list = $("#port443List");
  const publicPort = Number(payload.public_port || payload.port || payload.configured_port) || 443;
  const configuredPort = Number(payload.configured_port) || publicPort;
  $("#visualTitle").textContent = t("visualTitle").replace("{port}", publicPort);
  $("#visualText").textContent = t("visualText");
  $("#port443Number").textContent = String(publicPort);
  $("#port443Configured").textContent = configuredPort === publicPort ? t("port443Public") : t("port443Configured").replace("{port}", configuredPort);
  if (payload.error) {
    summary.textContent = t("port443Error");
    summary.className = "port-status error";
  } else if (!listeners.length) {
    summary.textContent = t("port443NoListeners");
    summary.className = "port-status warn";
  } else {
    summary.textContent = `${listeners.length} ${t("port443Listeners")}${routes.length ? ` · ${routes.length} ${t("port443Routes")}` : ""}`;
    summary.className = "port-status ok";
  }
  const listenerHtml = listeners.length ? listeners.map((item) => {
    const title = `${item.proto || ""} ${item.address || ""} · ${item.process || "unknown"}${item.pid ? ` · pid ${item.pid}` : ""}`;
    return `<article class="port-listener role-${escapeAttr(item.role || "other")}" title="${escapeAttr(title)}">
      <div>
        <strong>${escapeHtml(roleLabel(item.role))}</strong>
        <span>${escapeHtml(item.process || "unknown")}${item.pid ? ` · pid ${escapeHtml(item.pid)}` : ""}</span>
      </div>
      <small>${escapeHtml(item.proto || "--")} · ${escapeHtml(item.address || "--")}</small>
    </article>`;
  }).join("") : `<div class="port-empty">${escapeHtml(payload.error || t("port443NoListeners"))}</div>`;
  const routeHtml = routes.length ? routes.map((item) => {
    const via = item.via ? t("port443Via").replace("{value}", item.via) : "";
    const title = `${item.public || ""} → ${item.target || ""} · ${item.process || ""}`;
    return `<article class="port-listener role-${escapeAttr(item.role || "other")}" title="${escapeAttr(title)}">
      <div>
        <strong>${escapeHtml(roleLabel(item.role))}</strong>
        <span>${escapeHtml(item.process || "unknown")}${item.status ? ` · ${escapeHtml(statusLabel(item.status))}` : ""}</span>
      </div>
      <small>${escapeHtml(item.public || "--")} → ${escapeHtml(item.target || "--")}${via ? ` · ${escapeHtml(via)}` : ""}</small>
    </article>`;
  }).join("") : `<div class="port-empty">${escapeHtml(t("port443NoRoutes"))}</div>`;
  list.innerHTML = `
    <div class="port-section-label">${escapeHtml(t("port443PublicSection").replace("{port}", publicPort))}</div>
    ${listenerHtml}
    <div class="port-section-label">${escapeHtml(t("port443BehindSection").replace("{port}", publicPort))}</div>
    ${routeHtml}
  `;
}

function renderOverview() {
  const data = state.overview;
  if (!data) return;
  const cfg = data.config || {};
  const stats = data.stats_current || {};
  const bind = data.admin_bind || {};
  $("#sidebarVersion").textContent = `v${data.version || "--"}`;
  $("#sidebarBind").textContent = `${bind.host || "127.0.0.1"}:${bind.port || 1984}`;
  $("#settingsBind").textContent = `${bind.host || "127.0.0.1"}:${bind.port || 1984}`;
  $("#metricMode").textContent = cfg.mode || "--";
  renderSiteStatus();
  if (state.routingDirty && state.routingPreviewMap) {
    renderPortMap(state.routingPreviewMap);
  } else if (!state.routingDirty) {
    renderPortMap(data.port_map || data.port_443 || {});
  }
  $("#metricUsers").textContent = data.users_count ?? 0;
  $("#metricProxyTraffic").textContent = fmtBytes(stats.proxy_bytes);
  $("#metricProxyPackets").textContent = `${stats.proxy_pkts || 0} ${t("packets")}`;
  $("#metricSiteTraffic").textContent = fmtBytes(stats.site_bytes);
  $("#metricSitePackets").textContent = `${stats.site_pkts || 0} ${t("packets")}`;
  $("#lastRefresh").textContent = fmtDate(Math.floor(Date.now() / 1000));
  renderServices(data.services || {});
  renderRuntime();
  renderStats();
  renderBackups(data.backups || []);
  renderConfig();
}

function statsPayload() {
  if (state.stats) return state.stats;
  return {
    current: state.overview?.stats_current || {},
    history: state.overview?.stats_history || [],
    status: state.overview?.stats_status || {},
    summary_rows: [],
  };
}

function updateTrafficControls() {
  $$("[data-traffic-range]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.trafficRange === state.trafficRange);
  });
  $$("[data-traffic-view]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.trafficView === state.trafficView);
  });
}

function updateUserTrafficControls() {
  $$("[data-user-traffic-range]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.userTrafficRange === state.userTrafficRange);
  });
  $$("[data-user-traffic-view]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.userTrafficView === state.userTrafficView);
  });
}

function trafficRangeLabel(range) {
  const labels = {
    "15m": t("range15m"),
    "1h": t("range1h"),
    "24h": t("range24h"),
    month: t("rangeMonth"),
  };
  return labels[range] || range;
}

function rangeSeconds(range) {
  return {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "24h": 24 * 60 * 60,
    month: 30 * 24 * 60 * 60,
  }[range] || 60 * 60;
}

function filterTrafficRows(rows, range = state.trafficRange) {
  if (!Array.isArray(rows) || !rows.length) return [];
  const latest = Math.max(...rows.map((row) => Number(row.epoch) || 0));
  const cutoff = latest - rangeSeconds(range);
  return rows.filter((row) => (Number(row.epoch) || 0) >= cutoff);
}

function bucketTrafficRows(rows) {
  const filtered = filterTrafficRows(rows);
  if (filtered.length <= 140) return filtered;
  const chunk = Math.ceil(filtered.length / 120);
  const buckets = [];
  for (let i = 0; i < filtered.length; i += chunk) {
    const slice = filtered.slice(i, i + chunk);
    const last = slice[slice.length - 1];
    buckets.push({
      epoch: last.epoch,
      proxy_delta: slice.reduce((sum, item) => sum + (Number(item.proxy_delta) || 0), 0),
      site_delta: slice.reduce((sum, item) => sum + (Number(item.site_delta) || 0), 0),
      proxy_bytes: last.proxy_bytes,
      site_bytes: last.site_bytes,
    });
  }
  return buckets;
}

function fallbackTrafficSummaries(rows) {
  return trafficRanges.map((range) => {
    const windowRows = filterTrafficRows(rows, range);
    if (!windowRows.length) {
      return { range, points: 0, proxy_delta: 0, site_delta: 0, proxy_total: 0, site_total: 0 };
    }
    const first = windowRows[0];
    const last = windowRows[windowRows.length - 1];
    return {
      range,
      points: windowRows.length,
      proxy_delta: windowRows.reduce((sum, item) => sum + Math.max(0, Number(item.proxy_delta) || 0), 0),
      site_delta: windowRows.reduce((sum, item) => sum + Math.max(0, Number(item.site_delta) || 0), 0),
      proxy_total: Number(last.proxy_bytes) || 0,
      site_total: Number(last.site_bytes) || 0,
    };
  });
}

function renderTrafficLoading() {
  $("#trafficChart").classList.toggle("is-hidden", state.trafficView !== "chart");
  $("#trafficTableWrap").classList.toggle("is-hidden", state.trafficView !== "table");
  $("#trafficChart").innerHTML = `<div class="empty-chart"><strong>${escapeHtml(t("loading"))}</strong></div>`;
  $("#historyTable").innerHTML = `<tr><td colspan="5" class="empty-cell">${escapeHtml(t("loading"))}</td></tr>`;
}

function renderStats() {
  const payload = statsPayload();
  const status = payload.status || {};
  const stats = payload.current || {};
  const historyRows = payload.history || [];
  const summaryRows = payload.summary_rows?.length ? payload.summary_rows : fallbackTrafficSummaries(historyRows);
  $("#statsHealth").className = `status-pill health-${escapeAttr(status.health || "unknown")}`;
  $("#statsHealth").textContent = healthLabel(status.health);
  $("#collectorState").textContent = status.service ? statusLabel(status.service) : "--";
  $("#lastStatsPoint").textContent = status.last_ts ? fmtDate(status.last_ts) : t("never");
  $("#historyRows").textContent = status.history_rows ?? historyRows.length;
  $("#repairStatsBtn").classList.toggle("attention", status.health !== "ok");
  $("#collectStatsBtn").disabled = status.service === "not_installed";
  $("#metricProxyTraffic").textContent = fmtBytes(stats.proxy_bytes);
  $("#metricSiteTraffic").textContent = fmtBytes(stats.site_bytes);
  updateTrafficControls();
  if (state.trafficLoading) {
    renderTrafficLoading();
    return;
  }
  $("#trafficChart").classList.toggle("is-hidden", state.trafficView !== "chart");
  $("#trafficTableWrap").classList.toggle("is-hidden", state.trafficView !== "table");
  drawTrafficChart(historyRows);
  renderHistoryTable(summaryRows);
}

function drawTrafficChart(rows) {
  const el = $("#trafficChart");
  const points = bucketTrafficRows(rows);
  const proxyColor = getComputedStyle(document.documentElement).getPropertyValue("--blue").trim() || "#2563eb";
  const siteColor = getComputedStyle(document.documentElement).getPropertyValue("--green").trim() || "#0f9f6e";
  if (points.length < 2) {
    el.innerHTML = `<div class="empty-chart">
      <strong>${escapeHtml(points.length ? t("noTrafficForRange") : t("noHistory"))}</strong>
      <span>${escapeHtml(state.overview?.stats_status?.health === "ok" ? t("statsOk") : t("statsMissing"))}</span>
    </div>`;
    return;
  }
  const width = 900;
  const height = 300;
  const pad = { l: 54, r: 22, t: 24, b: 42 };
  const max = Math.max(1, ...points.map((p) => Math.max(p.proxy_delta || 0, p.site_delta || 0)));
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const toX = (i) => pad.l + (plotW * i) / Math.max(1, points.length - 1);
  const toY = (v) => pad.t + plotH - ((v || 0) / max) * plotH;
  const pathFor = (key) => points.map((p, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(p[key]).toFixed(1)}`).join(" ");
  const grid = Array.from({ length: 5 }, (_, i) => {
    const y = pad.t + (plotH / 4) * i;
    return `<line x1="${pad.l}" y1="${y}" x2="${width - pad.r}" y2="${y}"></line>`;
  }).join("");
  const axis = t("chartMax").replace("{value}", fmtBytes(max));
  el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeAttr(t("ariaTrafficHistory"))}">
    <g class="grid">${grid}</g>
    <path class="area proxy-area" d="${pathFor("proxy_delta")} L${width - pad.r},${height - pad.b} L${pad.l},${height - pad.b} Z"></path>
    <path class="line proxy-line" d="${pathFor("proxy_delta")}"></path>
    <path class="line site-line" d="${pathFor("site_delta")}"></path>
    <text x="${pad.l}" y="17" class="axis">${escapeHtml(axis)}</text>
    <text x="${pad.l}" y="${height - 12}" class="legend" fill="${proxyColor}">${escapeHtml(t("chartProxy"))}</text>
    <text x="${pad.l + 86}" y="${height - 12}" class="legend" fill="${siteColor}">${escapeHtml(t("chartSite"))}</text>
  </svg>`;
}

function renderHistoryTable(rows) {
  if (!rows.length) {
    $("#historyTable").innerHTML = `<tr><td colspan="5" class="empty-cell">${escapeHtml(t("noHistory"))}</td></tr>`;
    return;
  }
  $("#historyTable").innerHTML = rows.map((row) => `
    <tr>
      <td data-label="${escapeAttr(t("tablePeriod"))}"><strong>${escapeHtml(trafficRangeLabel(row.range))}</strong><small>${escapeHtml(row.points ? `${row.points} ${t("historyRows").toLowerCase()}` : t("noTrafficForRange"))}</small></td>
      <td data-label="${escapeAttr(t("tableProxyDelta"))}">${escapeHtml(fmtBytes(row.proxy_delta))}</td>
      <td data-label="${escapeAttr(t("tableSiteDelta"))}">${escapeHtml(fmtBytes(row.site_delta))}</td>
      <td data-label="${escapeAttr(t("tableProxyTotal"))}">${escapeHtml(fmtBytes(row.proxy_total))}</td>
      <td data-label="${escapeAttr(t("tableSiteTotal"))}">${escapeHtml(fmtBytes(row.site_total))}</td>
    </tr>
  `).join("");
}

function ensureUserTrafficSelection() {
  if (state.userTrafficUser && state.users.some((user) => user.name === state.userTrafficUser)) return;
  state.userTrafficUser = state.users[0]?.name || "";
}

async function selectUserTraffic(name, options = {}) {
  const next = String(name || "");
  if (!next || !state.users.some((user) => user.name === next)) return;
  const changed = state.userTrafficUser !== next;
  state.userTrafficUser = next;
  if (changed) {
    state.userTraffic = null;
  }
  renderUsers();
  renderUserTraffic();
  if (options.scroll) {
    $("#userTrafficPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  try {
    await refreshUserTraffic({ showLoading: true });
  } catch (err) {
    toast(err.message);
  }
}

function userTrafficRows() {
  return state.userTraffic?.history || [];
}

function bucketUserTrafficRows(rows) {
  const filtered = filterTrafficRows(rows, state.userTrafficRange);
  if (filtered.length <= 140) return filtered;
  const chunk = Math.ceil(filtered.length / 120);
  const buckets = [];
  for (let i = 0; i < filtered.length; i += chunk) {
    const slice = filtered.slice(i, i + chunk);
    const last = slice[slice.length - 1];
    buckets.push({
      epoch: last.epoch,
      total_delta: slice.reduce((sum, item) => sum + (Number(item.total_delta) || 0), 0),
      total_octets: last.total_octets,
      current_connections: last.current_connections,
      active_unique_ips: last.active_unique_ips,
    });
  }
  return buckets;
}

function fallbackUserTrafficSummaries(rows) {
  return trafficRanges.map((range) => {
    const windowRows = filterTrafficRows(rows, range);
    if (!windowRows.length) {
      return { range, points: 0, total_delta: 0, total_octets: 0 };
    }
    const last = windowRows[windowRows.length - 1];
    return {
      range,
      points: windowRows.length,
      total_delta: windowRows.reduce((sum, item) => sum + Math.max(0, Number(item.total_delta) || 0), 0),
      total_octets: Number(last.total_octets) || 0,
    };
  });
}

function renderUserTrafficLoading() {
  $("#userTrafficChart").classList.toggle("is-hidden", state.userTrafficView !== "chart");
  $("#userTrafficTableWrap").classList.toggle("is-hidden", state.userTrafficView !== "table");
  $("#userTrafficChart").innerHTML = `<div class="empty-chart"><strong>${escapeHtml(t("loading"))}</strong></div>`;
  $("#userTrafficTable").innerHTML = `<tr><td colspan="3" class="empty-cell">${escapeHtml(t("loading"))}</td></tr>`;
}

function drawUserTrafficChart(rows) {
  const el = $("#userTrafficChart");
  const points = bucketUserTrafficRows(rows);
  const color = getComputedStyle(document.documentElement).getPropertyValue("--blue").trim() || "#2563eb";
  if (points.length < 2) {
    el.innerHTML = `<div class="empty-chart">
      <strong>${escapeHtml(state.userTrafficUser ? t("noTrafficForRange") : t("selectUserTraffic"))}</strong>
      <span>${escapeHtml(state.userTraffic?.status?.runtime_ok ? t("statsOk") : t("trafficRuntimeUnavailable"))}</span>
    </div>`;
    return;
  }
  const width = 900;
  const height = 260;
  const pad = { l: 54, r: 22, t: 24, b: 42 };
  const max = Math.max(1, ...points.map((p) => Number(p.total_delta) || 0));
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const toX = (i) => pad.l + (plotW * i) / Math.max(1, points.length - 1);
  const toY = (v) => pad.t + plotH - ((v || 0) / max) * plotH;
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(p.total_delta).toFixed(1)}`).join(" ");
  const grid = Array.from({ length: 5 }, (_, i) => {
    const y = pad.t + (plotH / 4) * i;
    return `<line x1="${pad.l}" y1="${y}" x2="${width - pad.r}" y2="${y}"></line>`;
  }).join("");
  const axis = t("chartMax").replace("{value}", fmtBytes(max));
  el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeAttr(t("ariaTrafficHistory"))}">
    <g class="grid">${grid}</g>
    <path class="area proxy-area" d="${path} L${width - pad.r},${height - pad.b} L${pad.l},${height - pad.b} Z"></path>
    <path class="line proxy-line" d="${path}"></path>
    <text x="${pad.l}" y="17" class="axis">${escapeHtml(axis)}</text>
    <text x="${pad.l}" y="${height - 12}" class="legend" fill="${color}">${escapeHtml(state.userTrafficUser || t("users"))}</text>
  </svg>`;
}

function renderUserTrafficTable(rows) {
  if (!rows.length) {
    $("#userTrafficTable").innerHTML = `<tr><td colspan="3" class="empty-cell">${escapeHtml(t("noHistory"))}</td></tr>`;
    return;
  }
  $("#userTrafficTable").innerHTML = rows.map((row) => `
    <tr>
      <td data-label="${escapeAttr(t("tablePeriod"))}"><strong>${escapeHtml(trafficRangeLabel(row.range))}</strong><small>${escapeHtml(row.points ? `${row.points} ${t("historyRows").toLowerCase()}` : t("noTrafficForRange"))}</small></td>
      <td data-label="${escapeAttr(t("tableTrafficDelta"))}">${escapeHtml(fmtBytes(row.total_delta))}</td>
      <td data-label="${escapeAttr(t("tableTrafficTotal"))}">${escapeHtml(fmtBytes(row.total_octets))}</td>
    </tr>
  `).join("");
}

function renderUserTraffic() {
  updateUserTrafficControls();
  if (!state.userTrafficUser) {
    $("#userTrafficTitle").textContent = t("userTrafficTitle");
    $("#userTrafficHealth").className = "status-pill health-unknown";
    $("#userTrafficHealth").textContent = "--";
    $("#userTrafficTotal").textContent = "--";
    $("#userTrafficConnections").textContent = "--";
    $("#userTrafficIps").textContent = "--";
    $("#userTrafficChart").innerHTML = `<div class="empty-chart"><strong>${escapeHtml(t("selectUserTraffic"))}</strong></div>`;
    $("#userTrafficTable").innerHTML = `<tr><td colspan="3" class="empty-cell">${escapeHtml(t("selectUserTraffic"))}</td></tr>`;
    return;
  }
  $("#userTrafficTitle").textContent = `${t("userTrafficTitle")}: ${state.userTrafficUser}`;
  if (state.userTrafficLoading) {
    renderUserTrafficLoading();
    return;
  }
  const payload = state.userTraffic || {};
  const current = payload.current || {};
  const rows = userTrafficRows();
  const last = rows[rows.length - 1] || {};
  const total = Number(current.total_octets) || Number(last.total_octets) || 0;
  $("#userTrafficHealth").className = `status-pill ${current.enabled === false ? "health-stopped" : (current.ok ? "health-ok" : "health-stale")}`;
  $("#userTrafficHealth").textContent = current.enabled === false ? t("disabled") : (current.ok ? t("healthOk") : t("trafficRuntimeUnavailable"));
  $("#userTrafficTotal").textContent = fmtBytes(total);
  $("#userTrafficConnections").textContent = current.current_connections ?? last.current_connections ?? 0;
  $("#userTrafficIps").textContent = current.active_unique_ips ?? last.active_unique_ips ?? 0;
  $("#userTrafficChart").classList.toggle("is-hidden", state.userTrafficView !== "chart");
  $("#userTrafficTableWrap").classList.toggle("is-hidden", state.userTrafficView !== "table");
  drawUserTrafficChart(rows);
  renderUserTrafficTable(payload.summary_rows?.length ? payload.summary_rows : fallbackUserTrafficSummaries(rows));
}

function renderUsers() {
  const container = $("#usersTable");
  if (!state.users.length) {
    container.innerHTML = `<div class="empty empty-cell">${escapeHtml(t("noKeys"))}</div>`;
    return;
  }
  container.innerHTML = state.users.map((user) => {
    const pending = state.pendingUsers.has(user.name);
    const selected = user.name === state.userTrafficUser;
    const traffic = user.traffic || {};
    const trafficTotal = Number(traffic.total_octets) ? fmtBytes(traffic.total_octets) : "--";
    const activeIps = Number(traffic.active_unique_ips) || 0;
    const maxUniqueIps = Number.isFinite(Number(user.max_unique_ips)) ? Math.max(0, Number(user.max_unique_ips)) : 0;
    const warp = user.warp || {};
    const warpLabel = warp.mode === "warp_plus" ? "WARP+" : (warp.mode === "warp" ? "WARP" : "");
    return `
    <article class="key-card ${user.enabled ? "" : "disabled-row"} ${pending ? "pending-row" : ""} ${selected ? "selected-row" : ""}" data-select-user-traffic="${escapeAttr(user.name)}" aria-selected="${selected ? "true" : "false"}">
      <div class="key-card-user">
        <span class="field-label">${escapeHtml(t("tableUser"))}</span>
        <button class="key-name-button" type="button" data-user-traffic="${escapeAttr(user.name)}">
          <strong>${escapeHtml(user.name)}</strong>${user.main ? ` <small>${escapeHtml(t("main"))}</small>` : ""}
        </button>
        <div class="status-control">
          <label class="switch" title="${escapeAttr(user.main ? t("main") : (user.enabled ? t("disableKey") : t("enableKey")))}">
            <input type="checkbox" data-toggle-user="${escapeAttr(user.name)}" ${user.enabled ? "checked" : ""} ${user.main || pending ? "disabled" : ""}>
            <span></span>
          </label>
          <strong class="${user.enabled ? "state-on" : "state-off"}">${escapeHtml(pending ? t("applying") : (user.enabled ? t("enabled") : t("disabled")))}</strong>
        </div>
        ${warpLabel ? `<span class="warp-badge ${warp.enabled ? "active" : ""}" title="${escapeAttr(warp.source || "")}">${escapeHtml(warpLabel)}</span>` : ""}
      </div>
      <div class="key-card-secret">
        <span class="field-label">${escapeHtml(t("tableSecret"))}</span>
        <code title="${escapeAttr(user.secret)}">${escapeHtml(user.secret)}</code>
      </div>
      <div class="key-card-links">
        <span class="field-label">${escapeHtml(t("tableLink"))}</span>
        <div class="mini-actions">
          <button class="soft" data-copy="${escapeAttr(user.link)}" ${user.enabled ? "" : "disabled"}>${escapeHtml(t("copyLink"))}</button>
          <button class="soft" data-user-qr="${escapeAttr(user.name)}">${escapeHtml(t("showQr"))}</button>
        </div>
      </div>
      <div class="key-card-traffic">
        <span class="field-label">${escapeHtml(t("tableTraffic"))}</span>
        <div class="traffic-cell">
          <div class="traffic-main">
            <span>
              <strong>${escapeHtml(trafficTotal)}</strong>
              <small>${escapeHtml(activeIps ? `${activeIps} ${t("activeIps")}` : fmtDate(traffic.epoch))}</small>
            </span>
            <button class="soft" data-user-traffic="${escapeAttr(user.name)}">${escapeHtml(t("openStats"))}</button>
          </div>
          <form class="ip-limit-control" data-ip-limit-form="${escapeAttr(user.name)}" title="${escapeAttr(t("ipLimitHint"))}">
            <span>${escapeHtml(t("ipLimit"))}</span>
            <input type="number" min="0" max="1000000" step="1" value="${escapeAttr(maxUniqueIps)}" data-ip-limit-input="${escapeAttr(user.name)}" aria-label="${escapeAttr(t("ipLimit"))}: ${escapeAttr(user.name)}">
            <button class="soft" type="submit" data-ip-limit-save="${escapeAttr(user.name)}">${escapeHtml(t("saveIpLimit"))}</button>
          </form>
        </div>
      </div>
      <div class="key-card-actions">
        <span class="field-label">${escapeHtml(t("tableActions"))}</span>
        <div class="action-buttons">
          <button class="soft" data-copy="${escapeAttr(user.secret)}">${escapeHtml(t("copySecret"))}</button>
          <button class="danger" data-delete="${escapeAttr(user.name)}" ${user.main ? "disabled" : ""}>${escapeHtml(t("delete"))}</button>
        </div>
      </div>
    </article>
  `; }).join("");
}

function renderWarpSettings() {
  const cfg = state.warp || state.overview?.warp || {};
  const runtime = cfg.runtime || {};
  const modeEl = $("#warpMode");
  const scopeEl = $("#warpScope");
  const userEl = $("#warpUserSelect");
  if (!modeEl || !scopeEl || !userEl) return;
  modeEl.value = cfg.mode || "off";
  scopeEl.value = cfg.scope || "all";
  userEl.innerHTML = state.users.map((user) => `<option value="${escapeAttr(user.name)}">${escapeHtml(user.name)}</option>`).join("");
  userEl.value = cfg.user && state.users.some((user) => user.name === cfg.user) ? cfg.user : (state.users[0]?.name || "");
  $("#warpUserRow").hidden = scopeEl.value !== "user";
  const mask = scopeEl.value === "user"
    ? (cfg.users?.[userEl.value]?.license_mask || "")
    : (cfg.license_mask || "");
  $("#warpLicenseKey").placeholder = mask ? `${t("savedKey")}: ${mask}` : "optional";
  $("#warpStatus").textContent = runtime.installed ? t("warpInstalled") : t("warpNotInstalled");
  $("#warpStatus").classList.toggle("ok", Boolean(runtime.installed));
  const statusLine = runtime.status ? ` ${runtime.status}` : "";
  $("#warpRuntimeNote").textContent = scopeEl.value === "user"
    ? `${t("warpPerUserNote")}${statusLine ? ` ${statusLine}` : ""}`
    : `${t("warpAllNote")}${statusLine ? ` ${statusLine}` : ""}`;
}

function renderBackups(backups) {
  const box = $("#backupsList");
  renderBackupSchedule();
  if (!backups.length) {
    box.innerHTML = `<div class="empty">${escapeHtml(t("noBackups"))}</div>`;
    return;
  }
  box.innerHTML = backups.map((item) => `
    <div class="backup-item">
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml(item.path)} · ${escapeHtml(fmtDate(item.mtime))}</span>
      </div>
      <div class="backup-actions">
        <span>${escapeHtml(fmtBytes(item.size))}${item.encrypted ? ` · ${escapeHtml(t("encrypted"))}` : ""}</span>
        <button class="soft" data-restore-backup="${escapeAttr(item.name)}" ${item.encrypted ? "disabled" : ""} title="${escapeAttr(item.encrypted ? t("encryptedRestoreCli") : t("restoreBackup"))}">${escapeHtml(t("restoreBackup"))}</button>
      </div>
    </div>
  `).join("");
}

function renderBackupSchedule() {
  const schedule = state.backupSchedule || state.overview?.backup_schedule || { frequency: "off" };
  const frequency = schedule.frequency || "off";
  $$("[data-backup-schedule]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.backupSchedule === frequency);
  });
  const next = schedule.next && schedule.next !== "n/a" ? schedule.next : "";
  $("#backupScheduleMeta").textContent = frequency === "off"
    ? t("scheduleDisabled")
    : t("scheduleNext").replace("{value}", next || (schedule.calendar || "--"));
}

function renderEvents() {
  const box = $("#events");
  if (!state.events.length) {
    box.innerHTML = `<div class="empty">${escapeHtml(t("noEvents"))}</div>`;
    return;
  }
  box.innerHTML = state.events.map((item) => `
    <div class="event">
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(item.detail || item.time.toLocaleTimeString())}</small>
    </div>
  `).join("");
}

function renderConfig() {
  const cfg = state.overview?.config || {};
  const site = state.overview?.site_status || {};
  const routing = state.routing || state.overview?.routing || {};
  const items = [
    [t("configMode"), cfg.mode || "--"],
    [t("routingPort"), routing.port || cfg.port || "--"],
    [t("routingMaskHost"), routing.mask_host || cfg.mask_host || cfg.domain || "--"],
    [t("configDomain"), cfg.domain || cfg.mask_host || "--"],
    [t("configSiteStatus"), siteStatusText(site)],
    [t("configTemplate"), cfg.template_id || cfg.template || "--"],
    [t("configVersion"), state.overview?.version || "--"],
    [t("bindAddress"), `${state.overview?.admin_bind?.host || "127.0.0.1"}:${state.overview?.admin_bind?.port || 1984}`],
  ];
  $("#configList").innerHTML = items.map(([label, value]) => `
    <div>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");
}

function routingSummary(payload) {
  const conflicts = payload?.conflicts || [];
  if (conflicts.length) {
    return `${t("routingBusy")}: ${conflicts.map((item) => `${item.process} ${item.address}`).join(", ")}`;
  }
  const listeners = payload?.listeners || [];
  const listenerText = listeners.length
    ? listeners.map((item) => `${item.process} ${item.address}`).join(", ")
    : t("routingOk");
  const mask = t("routingCurrentMask").replace("{value}", payload?.mask_host || "--");
  return `${listenerText}. ${mask}. ${t("routingPerUserNote")}`;
}

function routingControlPairs() {
  return [
    {
      port: $("#visualRoutingPort"),
      mask: $("#visualRoutingMaskHost"),
      note: $("#visualRoutingNote"),
    },
    {
      port: $("#routingPort"),
      mask: $("#routingMaskHost"),
      note: $("#routingRuntimeNote"),
    },
  ].filter((item) => item.port && item.mask);
}

function setRoutingControlValues(routing = {}) {
  if (state.routingDirty) return;
  routingControlPairs().forEach((item) => {
    if (document.activeElement === item.port || document.activeElement === item.mask) return;
    item.port.value = routing.port || 443;
    item.mask.value = routing.mask_host || "google.com";
  });
}

function syncRoutingControls(source) {
  const form = source?.closest?.("form");
  const port = form?.querySelector('[name="port"]')?.value ?? "";
  const mask = form?.querySelector('[name="mask_host"]')?.value ?? "";
  routingControlPairs().forEach((item) => {
    if (item.port !== source && document.activeElement !== item.port) item.port.value = port;
    if (item.mask !== source && document.activeElement !== item.mask) item.mask.value = mask;
  });
}

function markRoutingDirty(eventObj) {
  state.routingDirty = true;
  syncRoutingControls(eventObj.target);
}

function setRoutingNotes(routing = {}) {
  const conflicts = routing.conflicts || [];
  const message = routingSummary(routing);
  routingControlPairs().forEach((item) => {
    if (!item.note) return;
    item.note.textContent = message;
    item.note.classList.toggle("error", Boolean(conflicts.length));
  });
}

function renderRoutingSettings(payload = null) {
  const routing = payload || state.routing || state.overview?.routing || {};
  if (state.routingDirty && !payload) return;
  if (!payload) {
    setRoutingControlValues(routing);
  }
  const conflicts = routing.conflicts || [];
  $("#routingStatus").textContent = conflicts.length ? t("routingBusy") : t("routingOk");
  $("#routingStatus").className = `status-pill ${conflicts.length ? "health-error" : "health-ok"}`;
  setRoutingNotes(routing);
}

async function refreshAll() {
  if (state.refreshingAll) return;
  state.refreshingAll = true;
  const btn = $("#refreshBtn");
  btn.disabled = true;
  try {
    state.overview = await api("/api/overview");
    state.backupSchedule = state.overview.backup_schedule || state.backupSchedule;
    state.routing = state.overview.routing || state.routing;
    state.warp = state.overview.warp || state.warp;
    updateLanguageFromOverview(state.overview);
    state.users = await api("/api/users");
    ensureUserTrafficSelection();
    if (!state.stats) {
      state.stats = {
        current: state.overview.stats_current || {},
        history: state.overview.stats_history || [],
        status: state.overview.stats_status || {},
        summary_rows: [],
      };
    } else {
      state.stats = {
        ...state.stats,
        current: state.overview.stats_current || state.stats.current || {},
        status: state.overview.stats_status || state.stats.status || {},
      };
    }
    renderOverview();
    renderUsers();
    renderRoutingSettings();
    renderWarpSettings();
    if (state.page === "traffic") {
      await refreshStats();
    } else if (state.page === "keys") {
      ensureUserTrafficSelection();
      await refreshUserTraffic();
    }
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
    state.refreshingAll = false;
    updateAutoRefreshToggle();
  }
}

async function refreshUsers() {
  state.users = await api("/api/users");
  renderUsers();
}

async function refreshStats(options = {}) {
  if (options.showLoading) {
    state.trafficLoading = true;
    renderStats();
  }
  try {
    const data = await api(`/api/stats?range=${encodeURIComponent(state.trafficRange)}`);
    state.stats = data;
    return data;
  } finally {
    state.trafficLoading = false;
    renderStats();
  }
}

async function refreshUserTraffic(options = {}) {
  ensureUserTrafficSelection();
  if (!state.userTrafficUser) {
    renderUserTraffic();
    return null;
  }
  if (options.showLoading) {
    state.userTrafficLoading = true;
    renderUserTraffic();
  }
  try {
    const data = await api(`/api/users/${encodeURIComponent(state.userTrafficUser)}/traffic?range=${encodeURIComponent(state.userTrafficRange)}`);
    state.userTraffic = data;
    return data;
  } finally {
    state.userTrafficLoading = false;
    renderUserTraffic();
  }
}

async function changeTrafficRange(range) {
  const next = trafficRanges.includes(range) ? range : "1h";
  if (next === state.trafficRange && state.stats?.range === next) return;
  const previous = state.trafficRange;
  state.trafficRange = next;
  try {
    await refreshStats({ showLoading: true });
  } catch (err) {
    state.trafficRange = previous;
    state.trafficLoading = false;
    renderStats();
    toast(err.message);
  }
}

async function changeUserTrafficRange(range) {
  const next = trafficRanges.includes(range) ? range : "1h";
  if (next === state.userTrafficRange && state.userTraffic?.range === next) return;
  const previous = state.userTrafficRange;
  state.userTrafficRange = next;
  try {
    await refreshUserTraffic({ showLoading: true });
  } catch (err) {
    state.userTrafficRange = previous;
    state.userTrafficLoading = false;
    renderUserTraffic();
    toast(err.message);
  }
}

async function addUser(name) {
  const data = await api("/api/users", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  addEvent(t("keyCreated"), data.name);
  toast(t("keyCreated"));
  await refreshAll();
}

async function deleteUser(name) {
  await api(`/api/users/${encodeURIComponent(name)}`, { method: "DELETE" });
  addEvent(t("keyDeleted"), name);
  toast(t("keyDeleted"));
  await refreshAll();
}

async function setUserEnabled(name, enabled) {
  const previousUsers = state.users.map((user) => ({ ...user }));
  state.pendingUsers.add(name);
  state.users = state.users.map((user) => user.name === name ? { ...user, enabled } : user);
  renderUsers();
  try {
    const data = await api(`/api/users/${encodeURIComponent(name)}/enabled`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    });
    state.users = state.users.map((user) => user.name === name ? { ...user, enabled: data.enabled } : user);
    const message = data.enabled ? t("keyEnabled") : t("keyDisabled");
    addEvent(message, name);
    toast(t("changesApplyInBackground"));
    try {
      await refreshUsers();
    } catch (refreshErr) {
      toast(refreshErr.message);
    }
    setTimeout(() => refreshAll().catch((err) => toast(err.message)), 1400);
  } catch (err) {
    state.users = previousUsers;
    toast(err.message);
  } finally {
    state.pendingUsers.delete(name);
    renderUsers();
  }
}

async function setUserMaxUniqueIps(name, value) {
  const limit = Number.parseInt(value, 10);
  if (!Number.isFinite(limit) || limit < 0 || limit > 1000000) {
    toast(t("ipLimitHint"));
    return;
  }
  const form = $$("[data-ip-limit-form]").find((item) => item.dataset.ipLimitForm === name);
  const controls = form ? Array.from(form.querySelectorAll("input, button")) : [];
  controls.forEach((control) => { control.disabled = true; });
  try {
    const data = await api(`/api/users/${encodeURIComponent(name)}/max-ips`, {
      method: "POST",
      body: JSON.stringify({ max_unique_ips: limit }),
    });
    state.users = state.users.map((user) => user.name === name ? { ...user, max_unique_ips: data.max_unique_ips } : user);
    renderUsers();
    addEvent(t("ipLimitSaved"), `${name}: ${data.max_unique_ips}`);
    toast(t("changesApplyInBackground"));
    setTimeout(() => refreshAll().catch((err) => toast(err.message)), 1400);
  } catch (err) {
    toast(err.message);
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
}

async function checkRoutingPort(inputEl = $("#routingPort")) {
  const port = Number.parseInt(inputEl?.value, 10);
  if (!Number.isFinite(port) || port < 1 || port > 65535) return;
  try {
    const data = await api(`/api/routing?port=${encodeURIComponent(port)}`);
    renderRoutingSettings(data);
    state.routingPreviewMap = {
      public_port: data.port,
      configured_port: state.routing?.port || state.overview?.routing?.port || data.port,
      listeners: data.listeners || [],
      routes: [],
      ok: data.ok,
      error: data.error,
    };
    renderPortMap(state.routingPreviewMap);
  } catch (err) {
    $("#routingStatus").textContent = t("routingBusy");
    $("#routingStatus").className = "status-pill health-error";
    routingControlPairs().forEach((item) => {
      if (!item.note) return;
      item.note.textContent = err.message;
      item.note.classList.add("error");
    });
  }
}

async function saveRoutingSettings(eventObj) {
  eventObj.preventDefault();
  const form = eventObj.currentTarget;
  const controls = Array.from(form.querySelectorAll("input, button"));
  const portInput = form.querySelector('[name="port"]');
  const maskInput = form.querySelector('[name="mask_host"]');
  controls.forEach((control) => { control.disabled = true; });
  try {
    const payload = {
      port: Number.parseInt(portInput?.value, 10),
      mask_host: String(maskInput?.value || "").trim(),
    };
    const data = await api("/api/routing", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.routingDirty = false;
    state.routingPreviewMap = null;
    state.routing = data;
    state.overview = await api("/api/overview");
    renderRoutingSettings();
    renderOverview();
    addEvent(t("routingSaved"), `${data.port} / ${data.mask_host}`);
    toast(t("routingSaved"));
    setTimeout(() => refreshAll().catch((err) => toast(err.message)), 1400);
  } catch (err) {
    toast(err.message);
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
}

async function saveWarpSettings(eventObj) {
  eventObj.preventDefault();
  const form = eventObj.currentTarget;
  const controls = Array.from(form.querySelectorAll("input, select, button"));
  controls.forEach((control) => { control.disabled = true; });
  try {
    const payload = {
      mode: $("#warpMode").value,
      scope: $("#warpScope").value,
      user: $("#warpUserSelect").value,
      license_key: $("#warpLicenseKey").value.trim(),
    };
    const data = await api("/api/warp", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.warp = data.config;
    $("#warpLicenseKey").value = "";
    renderWarpSettings();
    const warning = data.apply?.warnings?.[0] || "";
    toast(warning || t("warpSaved"));
    addEvent(t("warpSaved"), payload.scope === "user" ? payload.user : payload.mode);
    await refreshAll();
  } catch (err) {
    toast(err.message);
  } finally {
    controls.forEach((control) => { control.disabled = false; });
  }
}

async function createBackup() {
  const btn = $("#createBackupBtn");
  btn.disabled = true;
  try {
    const data = await api("/api/backups", { method: "POST", body: "{}" });
    addEvent(t("backupCreated"), data.path || "");
    toast(t("backupCreated"));
    await refreshAll();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
  }
}

async function setBackupSchedule(frequency) {
  $$("[data-backup-schedule]").forEach((btn) => { btn.disabled = true; });
  try {
    const data = await api("/api/backups/schedule", {
      method: "POST",
      body: JSON.stringify({ frequency }),
    });
    state.backupSchedule = data.schedule || data;
    renderBackupSchedule();
    addEvent(t("scheduleSaved"), frequency);
    toast(t("scheduleSaved"));
  } catch (err) {
    toast(err.message);
  } finally {
    $$("[data-backup-schedule]").forEach((btn) => { btn.disabled = false; });
  }
}

async function restoreBackup(name) {
  const data = await api("/api/backups/restore", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  addEvent(t("backupRestoreStarted"), data.name || name);
  toast(t("backupRestoreStarted"));
  setTimeout(() => refreshAll().catch((err) => toast(err.message)), 4000);
}

function showUserQr(name) {
  const user = state.users.find((item) => item.name === name);
  if (!user) {
    toast(t("qrUnavailable"));
    return;
  }
  state.qrLink = user.link || "";
  $("#qrTitle").textContent = `${t("qrTitle")} · ${user.name}`;
  $("#qrMeta").textContent = user.link || "";
  const img = $("#qrImage");
  img.alt = `${user.name} Telegram proxy QR`;
  img.onerror = () => {
    img.removeAttribute("src");
    toast(t("qrUnavailable"));
  };
  img.src = `/api/users/${encodeURIComponent(user.name)}/qr?ts=${Date.now()}`;
  $("#qrModal").hidden = false;
}

async function loadLogs() {
  const service = $("#logService").value;
  const btn = $("#loadLogsBtn");
  btn.disabled = true;
  $("#logsMeta").textContent = "";
  $("#logsBox").textContent = t("loading");
  try {
    const payload = await api(`/api/logs?service=${encodeURIComponent(service)}`);
    if ($("#logService").value === service) {
      const structured = payload && typeof payload === "object";
      const text = typeof payload === "string" ? payload : (payload?.text || "");
      const lines = structured ? (payload.line_count ?? text.split("\n").filter(Boolean).length) : text.split("\n").filter(Boolean).length;
      const stateText = structured ? (payload.ok ? "OK" : `exit ${payload.exit_code ?? "?"}`) : "OK";
      $("#logsMeta").textContent = `${service} · ${lines} ${t("logsLines")} · ${stateText}`;
      $("#logsBox").textContent = text || t("logsNoData");
    }
  } catch (err) {
    $("#logsMeta").textContent = "";
    $("#logsBox").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

async function restartService(name) {
  await api(`/api/services/${encodeURIComponent(name)}/restart`, { method: "POST", body: "{}" });
  addEvent(t("serviceRestarted"), name);
  toast(`${name} ${t("serviceRestarted").toLowerCase()}`);
  await refreshAll();
}

async function repairStats() {
  const btn = $("#repairStatsBtn");
  btn.disabled = true;
  try {
    await api("/api/stats/repair", { method: "POST", body: "{}" });
    addEvent(t("statsRepaired"));
    toast(t("statsRepaired"));
    await refreshAll();
    await refreshStats();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
  }
}

async function collectStats() {
  const btn = $("#collectStatsBtn");
  btn.disabled = true;
  try {
    await api("/api/stats/collect", { method: "POST", body: "{}" });
    addEvent(t("statsCollected"));
    toast(t("statsCollected"));
    await refreshAll();
    await refreshStats();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
  }
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value);
    toast(t("copied"));
  } catch (_) {
    const area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    toast(ok ? t("copied") : t("copyFailed"));
  }
}

document.addEventListener("click", async (eventObj) => {
  const nav = eventObj.target.closest("[data-nav]");
  if (nav) {
    setPage(nav.dataset.nav);
    return;
  }

  const button = eventObj.target.closest("button");
  if (button) {
    if (button.id === "themeToggle") {
      setTheme(state.theme === "dark" ? "light" : "dark");
    } else if (button.id === "menuBtn") {
      $("#sidebar").classList.toggle("open");
    } else if (button.dataset.trafficRange) {
      changeTrafficRange(button.dataset.trafficRange);
    } else if (button.dataset.trafficView) {
      state.trafficView = button.dataset.trafficView === "table" ? "table" : "chart";
      renderStats();
    } else if (button.dataset.userTraffic) {
      selectUserTraffic(button.dataset.userTraffic, { scroll: true });
    } else if (button.dataset.userQr) {
      showUserQr(button.dataset.userQr);
    } else if (button.dataset.userTrafficRange) {
      changeUserTrafficRange(button.dataset.userTrafficRange);
    } else if (button.dataset.userTrafficView) {
      state.userTrafficView = button.dataset.userTrafficView === "table" ? "table" : "chart";
      renderUserTraffic();
    } else if (button.dataset.backupSchedule) {
      setBackupSchedule(button.dataset.backupSchedule);
    } else if (button.dataset.restoreBackup) {
      const name = button.dataset.restoreBackup;
      if (confirm(`${t("confirmRestoreBackup")} ${name}?`)) restoreBackup(name).catch((err) => toast(err.message));
    } else if (button.dataset.copy) {
      await copyText(button.dataset.copy);
    } else if (button.dataset.delete) {
      const name = button.dataset.delete;
      if (confirm(`${t("confirmDelete")} ${name}?`)) deleteUser(name).catch((err) => toast(err.message));
    } else if (button.dataset.restart) {
      const name = button.dataset.restart;
      if (confirm(`${t("confirmRestart")} ${name}?`)) restartService(name).catch((err) => toast(err.message));
    }
    return;
  }

  if (eventObj.target.closest("input, select, textarea, label, form")) return;
  const row = eventObj.target.closest("[data-select-user-traffic]");
  if (!row) return;
  selectUserTraffic(row.dataset.selectUserTraffic, { scroll: true });
});

document.addEventListener("change", (eventObj) => {
  const input = eventObj.target.closest("[data-toggle-user]");
  if (!input) return;
  input.disabled = true;
  setUserEnabled(input.dataset.toggleUser, input.checked).catch((err) => {
    input.checked = !input.checked;
    input.disabled = false;
    toast(err.message);
  });
});

$("#addUserForm").addEventListener("submit", (eventObj) => {
  eventObj.preventDefault();
  const input = $("#userName");
  const name = input.value.trim();
  if (!/^[A-Za-z0-9_.-]{1,48}$/.test(name)) {
    toast(t("invalidUser"));
    return;
  }
  input.value = "";
  addUser(name).catch((err) => toast(err.message));
});

document.addEventListener("submit", (eventObj) => {
  const form = eventObj.target.closest("[data-ip-limit-form]");
  if (!form) return;
  eventObj.preventDefault();
  const input = form.querySelector("[data-ip-limit-input]");
  setUserMaxUniqueIps(form.dataset.ipLimitForm, input?.value || "0");
});

$("#refreshBtn").addEventListener("click", refreshAll);
$("#autoRefreshToggle").addEventListener("click", () => setAutoRefresh(!state.autoRefreshEnabled));
$("#languageSelect").addEventListener("change", (eventObj) => setLanguage(eventObj.target.value));
$("#qrClose").addEventListener("click", () => {
  $("#qrModal").hidden = true;
});
$("#qrCopyBtn").addEventListener("click", () => {
  if (state.qrLink) copyText(state.qrLink);
});
$("#createBackupBtn").addEventListener("click", createBackup);
$("#loadLogsBtn").addEventListener("click", loadLogs);
$("#repairStatsBtn").addEventListener("click", repairStats);
$("#collectStatsBtn").addEventListener("click", collectStats);
$("#authSettingsForm").addEventListener("submit", updateAuthSettings);
$("#visualRoutingForm").addEventListener("submit", saveRoutingSettings);
$("#visualRoutingPort").addEventListener("input", markRoutingDirty);
$("#visualRoutingMaskHost").addEventListener("input", markRoutingDirty);
$("#visualRoutingPort").addEventListener("change", (eventObj) => checkRoutingPort(eventObj.target));
$("#routingSettingsForm").addEventListener("submit", saveRoutingSettings);
$("#routingPort").addEventListener("input", markRoutingDirty);
$("#routingMaskHost").addEventListener("input", markRoutingDirty);
$("#routingPort").addEventListener("change", (eventObj) => checkRoutingPort(eventObj.target));
$("#warpSettingsForm").addEventListener("submit", saveWarpSettings);
$("#warpScope").addEventListener("change", renderWarpSettings);
$("#warpUserSelect").addEventListener("change", renderWarpSettings);
window.addEventListener("hashchange", () => setPage((location.hash || "#dashboard").slice(1), false));

setPage((location.hash || "#dashboard").slice(1), false);
setTheme(state.theme);
renderEvents();
syncAutoRefreshTimer();
refreshAll();
loadLogs();
