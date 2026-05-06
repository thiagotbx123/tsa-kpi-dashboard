"""KPI Dashboard Local Server — serves dashboard + live refresh endpoint.

Usage:
  python scripts/kpi/serve_kpi.py          # starts on http://localhost:8787
  python scripts/kpi/serve_kpi.py --port 9000

Endpoints:
  GET /           → serves KPI_DASHBOARD.html
  POST /refresh   → runs full pipeline (refresh_linear_cache → merge → normalize → build) then returns updated HTML
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import subprocess
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8787
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(SCRIPT_DIR, '..', '..')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from team_config import OUTPUT_DIR
DASHBOARD_PATH = os.path.join(OUTPUT_DIR, 'KPI_DASHBOARD.html')
PYTHON = sys.executable


class KPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_dashboard()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/refresh':
            self._run_refresh()
        else:
            self.send_error(404)

    def _serve_dashboard(self):
        try:
            with open(DASHBOARD_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, 'Dashboard not found. Run orchestrate.py first.')

    def _run_refresh(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Refresh requested...")
        try:
            result = subprocess.run(
                [PYTHON, os.path.join(SCRIPT_DIR, 'orchestrate.py')],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=180,
            )
            ok = result.returncode == 0
            print(result.stdout)
            if result.stderr:
                print('STDERR:', result.stderr)

            self.send_response(200 if ok else 500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            import json
            self.wfile.write(json.dumps({
                'success': ok,
                'message': 'Pipeline complete' if ok else 'Pipeline failed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }).encode('utf-8'))
        except subprocess.TimeoutExpired:
            self.send_response(504)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":false,"message":"Pipeline timed out (180s)"}')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    server = HTTPServer(('127.0.0.1', PORT), KPIHandler)
    url = f'http://localhost:{PORT}'
    print(f'KPI Dashboard server running at {url}')
    print(f'Press Ctrl+C to stop\n')
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
        server.server_close()


if __name__ == '__main__':
    main()
