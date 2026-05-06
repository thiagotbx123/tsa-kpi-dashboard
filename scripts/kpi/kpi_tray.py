r"""
KPI Dashboard — System Tray Server
Runs pipeline, starts HTTP server + ngrok, sits in system tray.
Icon: green = all healthy, yellow = partial, red = both down.
"""
import sys
import os
import io

# pythonw has no stdout/stderr — redirect to log file before anything else
# N04: Must resolve before team_config import; uses same base as OUTPUT_DIR
_LOG_DIR = os.path.join(os.environ.get('KPI_OUTPUT_DIR', os.path.join(os.path.expanduser('~'), 'Downloads')), 'kpi-serve')
_LOG_PATH = os.path.join(_LOG_DIR, 'kpi_tray.log')
try:
    os.makedirs(_LOG_DIR, exist_ok=True)
except Exception:
    pass

def _safe_stream():
    """Ensure stdout/stderr are writable — pythonw sets them to None.
    Uses RotatingFileHandler: 5MB max, 3 backups."""
    import logging
    from logging.handlers import RotatingFileHandler
    for attr in ('stdout', 'stderr'):
        stream = getattr(sys, attr, None)
        if stream is None:
            try:
                handler = RotatingFileHandler(
                    _LOG_PATH, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
                handler.doRollover()
                setattr(sys, attr, handler.stream)
            except Exception:
                try:
                    setattr(sys, attr, open(_LOG_PATH, 'a', encoding='utf-8'))
                except Exception:
                    setattr(sys, attr, io.StringIO())
        else:
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

_safe_stream()

import subprocess
import threading
import time
import signal
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

import pystray
from PIL import Image, ImageDraw, ImageFont


# ─── Single Instance (PID lockfile) ───
_LOCK_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'kpi-serve', 'kpi_tray.pid')

def _kill_old_instance():
    """Kill previous tray instance if its PID file exists."""
    if os.path.exists(_LOCK_PATH):
        try:
            old_pid = int(open(_LOCK_PATH).read().strip())
            if old_pid != os.getpid():
                subprocess.run(['taskkill', '/F', '/PID', str(old_pid)],
                               capture_output=True, timeout=5)
                time.sleep(1)
        except Exception:
            pass
    # Write our PID
    os.makedirs(os.path.dirname(_LOCK_PATH), exist_ok=True)
    with open(_LOCK_PATH, 'w') as f:
        f.write(str(os.getpid()))


def _kill_orphan_ngrok():
    """Kill any stale ngrok.exe from previous sessions (B).
    ngrok free tier allows only 1 concurrent agent per reserved URL —
    an orphan process blocks the new tray from claiming the tunnel."""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'],
                       capture_output=True, timeout=5)
        time.sleep(1)
    except Exception:
        pass

_kill_old_instance()
_kill_orphan_ngrok()

# ─── Config ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from team_config import OUTPUT_DIR
SERVE_DIR = os.path.join(OUTPUT_DIR, 'kpi-serve')
DASHBOARD_SRC = os.path.join(OUTPUT_DIR, 'KPI_DASHBOARD.html')
ORCHESTRATE = os.path.join(SCRIPT_DIR, 'orchestrate.py')
ICO_PATH = os.path.join(SCRIPT_DIR, 'kpi_dashboard.ico')
NGROK_URL = os.environ.get('NGROK_URL', 'uneffused-hoyt-unpunctually.ngrok-free.dev')
PUBLIC_URL = f'https://{NGROK_URL}/KPI_DASHBOARD.html'
HTTP_PORT = int(os.environ.get('KPI_HTTP_PORT', '8080'))
HEALTH_INTERVAL = 30  # seconds between health checks


def _resolve_ngrok_bin():
    """Pick a working ngrok binary. The MSIX-stable build (resolved via
    WindowsApps shim) panics on startup with 'disabled updater should never run'
    — so prefer the npm-managed binary when present, fall back to PATH."""
    candidates = [
        os.environ.get('NGROK_BIN'),
        os.path.expanduser(r'~\AppData\Roaming\npm\node_modules\ngrok\bin\ngrok.exe'),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return 'ngrok'

NGROK_BIN = _resolve_ngrok_bin()

# ─── State ───
http_server = None
ngrok_proc = None
tray_icon = None
status = {'http': False, 'ngrok': False, 'last_build': None}


# ─── Icon generation ───
def make_icon(color='green'):
    """Create a simple colored circle icon with KPI text."""
    colors = {'green': '#27AE60', 'yellow': '#F39C12', 'red': '#E74C3C', 'gray': '#95A5A6'}
    fill = colors.get(color, colors['gray'])
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Filled circle
    draw.ellipse([4, 4, 60, 60], fill=fill)
    # "K" letter in center
    try:
        font = ImageFont.truetype('segoeui.ttf', 30)
    except Exception:
        font = ImageFont.load_default()
    draw.text((32, 32), 'K', fill='white', font=font, anchor='mm')
    return img


def load_ico():
    """Try to load .ico file, fallback to generated icon."""
    try:
        return Image.open(ICO_PATH)
    except Exception:
        return make_icon('gray')


# ─── Health checks ───
def check_http():
    try:
        r = urllib.request.urlopen(f'http://localhost:{HTTP_PORT}/KPI_DASHBOARD.html', timeout=3)
        return r.status == 200
    except Exception:
        return False


def check_ngrok():
    """Real health check (A):
    1) Local ngrok agent API must be up on :4040
    2) The tunnel must list our expected PUBLIC_URL
    3) The PUBLIC_URL must respond 2xx/3xx from the outside
       (proves ngrok server actually sees us online, not just the local agent).
    Returns False on any failure — triggers auto-restart in health_loop.
    """
    import json
    try:
        r = urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels', timeout=3)
        if r.status != 200:
            return False
        data = json.loads(r.read().decode('utf-8', errors='replace'))
        tunnels = data.get('tunnels') or []
        expected = f'https://{NGROK_URL}'
        if not any(t.get('public_url') == expected for t in tunnels):
            return False
    except Exception:
        return False
    # External reachability probe — distinguishes "agent alive but disconnected"
    # from "agent alive and online to the world" (ERR_NGROK_3200 root cause).
    try:
        req = urllib.request.Request(
            f'{expected}/KPI_DASHBOARD.html',
            method='HEAD',
            headers={'ngrok-skip-browser-warning': '1'},
        )
        r = urllib.request.urlopen(req, timeout=5)
        return 200 <= r.status < 400
    except Exception:
        return False


def get_status_color():
    h, n = status['http'], status['ngrok']
    if h and n:
        return 'green'
    if h or n:
        return 'yellow'
    return 'red'


def get_status_text():
    h = 'OK' if status['http'] else 'DOWN'
    n = 'OK' if status['ngrok'] else 'DOWN'
    return f'KPI Dashboard  |  HTTP: {h}  |  ngrok: {n}'


# ─── Pipeline ───
def run_pipeline(full_refresh=False):
    """Run orchestrate.py to rebuild dashboard.
    full_refresh=False uses --skip-refresh (fast, <1s).
    full_refresh=True fetches fresh data from Linear API (~15s).
    """
    args = [sys.executable, ORCHESTRATE]
    if not full_refresh:
        args.append('--skip-refresh')
    try:
        r = subprocess.run(
            args, cwd=SCRIPT_DIR,
            capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0:
            status['last_build'] = time.strftime('%H:%M')
            os.makedirs(SERVE_DIR, exist_ok=True)
            if os.path.exists(DASHBOARD_SRC):
                import shutil
                shutil.copy2(DASHBOARD_SRC, SERVE_DIR)
            return True
        else:
            print(f'Pipeline error:\n{r.stderr}')
            return False
    except Exception as e:
        print(f'Pipeline exception: {e}')
        return False


# ─── HTTP Server ───
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silent

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


def start_http():
    global http_server
    if check_http():
        status['http'] = True
        return
    os.makedirs(SERVE_DIR, exist_ok=True)
    handler = partial(QuietHandler, directory=SERVE_DIR)
    try:
        http_server = ThreadingHTTPServer(('127.0.0.1', HTTP_PORT), handler)
        http_server.daemon_threads = True
        t = threading.Thread(target=http_server.serve_forever, daemon=True)
        t.start()
        time.sleep(1)
        status['http'] = check_http()
    except OSError as e:
        print(f'HTTP server error: {e}')
        status['http'] = False


def stop_http():
    global http_server
    if http_server:
        http_server.shutdown()
        http_server = None
    status['http'] = False


# ─── ngrok ───
def start_ngrok():
    global ngrok_proc
    if check_ngrok():
        status['ngrok'] = True
        return
    # If check failed but a ngrok process exists (stale/disconnected), kill it.
    # Free tier blocks a second agent claiming the same reserved URL otherwise.
    if ngrok_proc is not None:
        try:
            ngrok_proc.terminate()
            ngrok_proc.wait(timeout=3)
        except Exception:
            pass
        ngrok_proc = None
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    try:
        # Explicit 127.0.0.1 (not bare port, which ngrok resolves as
        # localhost → ::1/IPv6 first on Win11; HTTPServer is IPv4-only).
        ngrok_proc = subprocess.Popen(
            [NGROK_BIN, 'http', f'--url={NGROK_URL}',
             f'127.0.0.1:{HTTP_PORT}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(5)
        status['ngrok'] = check_ngrok()
    except FileNotFoundError:
        print(f'ngrok binary not found: {NGROK_BIN}')
        status['ngrok'] = False


def stop_ngrok():
    global ngrok_proc
    if ngrok_proc:
        ngrok_proc.terminate()
        ngrok_proc = None
    status['ngrok'] = False


# ─── Daily auto-refresh scheduler ───
AUTO_REFRESH_HOUR = 9
AUTO_REFRESH_MINUTE = 0

def auto_refresh_loop():
    """Run full refresh + rebuild daily at AUTO_REFRESH_HOUR:AUTO_REFRESH_MINUTE on weekdays."""
    last_run_date = None
    while True:
        now = time.localtime()
        today = (now.tm_year, now.tm_mon, now.tm_mday)
        is_weekday = now.tm_wday < 5  # Mon-Fri
        past_trigger = (now.tm_hour > AUTO_REFRESH_HOUR or
                        (now.tm_hour == AUTO_REFRESH_HOUR and now.tm_min >= AUTO_REFRESH_MINUTE))

        if is_weekday and past_trigger and last_run_date != today:
            last_run_date = today
            print(f'[auto-refresh] Triggered at {time.strftime("%H:%M")}')
            if tray_icon:
                tray_icon.icon = make_icon('yellow')
                tray_icon.title = 'KPI Dashboard  |  Auto-refreshing...'
            ok = run_pipeline(full_refresh=True)
            if tray_icon:
                status['http'] = check_http()
                status['ngrok'] = check_ngrok()
                tray_icon.icon = make_icon(get_status_color())
                tray_icon.title = get_status_text() + (f'  |  Last: {status["last_build"]}' if status.get('last_build') else '')
            result = 'OK' if ok else 'FAILED'
            print(f'[auto-refresh] {result} at {time.strftime("%H:%M")}')
            _notify('KPI Auto-Refresh', f'Daily refresh {result} at {time.strftime("%H:%M")}')

        time.sleep(30)


# ─── Health monitor ───
def health_loop():
    while True:
        time.sleep(HEALTH_INTERVAL)
        status['http'] = check_http()
        status['ngrok'] = check_ngrok()

        # Auto-restart if down
        if not status['http']:
            start_http()
        if not status['ngrok']:
            start_ngrok()

        # Update tray icon
        if tray_icon:
            tray_icon.icon = make_icon(get_status_color())
            tray_icon.title = get_status_text()


# ─── Windows notifications ───
def _notify(title, msg):
    """Show a Windows toast notification (non-blocking, best-effort)."""
    try:
        from subprocess import Popen
        ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t.GetElementsByTagName("text")[0].AppendChild($t.CreateTextNode("{title}")) > $null
$t.GetElementsByTagName("text")[1].AppendChild($t.CreateTextNode("{msg}")) > $null
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("KPI Dashboard").Show([Windows.UI.Notifications.ToastNotification]::new($t))
'''
        Popen(['powershell', '-WindowStyle', 'Hidden', '-Command', ps],
              creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


# ─── Tray menu actions ───
def on_open_dashboard(icon, item):
    os.startfile(PUBLIC_URL)


def on_open_local(icon, item):
    os.startfile(f'http://localhost:{HTTP_PORT}/KPI_DASHBOARD.html')


def _run_with_feedback(icon, full_refresh):
    """Shared pipeline runner with visual feedback and notification."""
    mode = 'Full Refresh' if full_refresh else 'Quick Rebuild'
    icon.icon = make_icon('yellow')
    icon.title = f'KPI Dashboard  |  {mode}...'
    ok = run_pipeline(full_refresh=full_refresh)
    status['http'] = check_http()
    status['ngrok'] = check_ngrok()
    icon.icon = make_icon(get_status_color())
    icon.title = get_status_text() + (f'  |  Last: {status["last_build"]}' if status.get('last_build') else '')
    if ok:
        _notify('KPI Dashboard', f'{mode} completed at {status.get("last_build", "?")}')
    else:
        _notify('KPI Dashboard', f'{mode} FAILED — check logs')


def on_refresh_and_rebuild(icon, item):
    """Full refresh from Linear API + rebuild dashboard."""
    threading.Thread(target=_run_with_feedback, args=(icon, True), daemon=True).start()


def on_quick_rebuild(icon, item):
    """Rebuild from cached data (no API call, fast)."""
    threading.Thread(target=_run_with_feedback, args=(icon, False), daemon=True).start()


def _last_refresh_label(item):
    """Dynamic label showing last refresh time."""
    t = status.get('last_build')
    return f'Last refresh: {t}' if t else 'Last refresh: —'


def on_exit(icon, item):
    stop_ngrok()
    stop_http()
    icon.stop()


# ─── Main ───
def main():
    global tray_icon

    print('=' * 50)
    print('  KPI Dashboard — System Tray Server')
    print('=' * 50)

    # 1. Run full pipeline (Linear API refresh + rebuild)
    print('\n[1/4] Running full KPI pipeline (Linear API + rebuild)...')
    run_pipeline(full_refresh=True)

    # 2. Start servers
    print('[2/4] Starting HTTP server + ngrok...')
    start_http()
    start_ngrok()

    # 3. Open dashboard in browser
    print('[3/4] Opening dashboard...')
    status['http'] = check_http()
    status['ngrok'] = check_ngrok()
    import webbrowser
    if status['http']:
        webbrowser.open(f'http://localhost:{HTTP_PORT}/KPI_DASHBOARD.html')
    elif os.path.exists(DASHBOARD_SRC):
        os.startfile(DASHBOARD_SRC)

    # 4. Launch tray icon
    print('[4/4] Launching system tray icon...')

    menu = pystray.Menu(
        pystray.MenuItem('Open Dashboard', on_open_dashboard, default=True),
        pystray.MenuItem('Open Local', on_open_local),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Refresh & Rebuild (Linear API)', on_refresh_and_rebuild),
        pystray.MenuItem('Quick Rebuild (cached data)', on_quick_rebuild),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_last_refresh_label, None, enabled=False),
        pystray.MenuItem(lambda item: get_status_text(), None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Exit', on_exit),
    )

    tray_icon = pystray.Icon(
        name='KPI Dashboard',
        icon=make_icon(get_status_color()),
        title=get_status_text(),
        menu=menu,
    )

    # Start health monitor + daily auto-refresh
    threading.Thread(target=health_loop, daemon=True).start()
    threading.Thread(target=auto_refresh_loop, daemon=True).start()

    h = 'OK' if status['http'] else 'FAIL'
    n = 'OK' if status['ngrok'] else 'FAIL'
    print(f'\n  HTTP: {h}  |  ngrok: {n}')
    print(f'  URL: {PUBLIC_URL}')
    print(f'  Auto-refresh: weekdays at {AUTO_REFRESH_HOUR:02d}:{AUTO_REFRESH_MINUTE:02d}')
    print(f'\n  Tray icon active — right-click for options.')
    print('  Close from tray icon > Exit')

    # This blocks until icon.stop()
    tray_icon.run()


if __name__ == '__main__':
    main()
