"""Локальный dev-сервер: как nginx — /privacy → /privacy/, свои страницы ошибок. Запуск: python catalog-src/serve.py"""
import http.server, os, functools, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class H(http.server.SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        f = os.path.join(ROOT, "errors", f"{code}.html")
        if os.path.exists(f):
            body = open(f, "rb").read()
            self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            if self.command != "HEAD": self.wfile.write(body)
        else:
            super().send_error(code, message, explain)
    def do_POST(self):  # как nginx: /api/* → админка (127.0.0.1:5600)
        if not self.path.startswith("/api/"): return self.send_error(405)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        req = urllib.request.Request("http://127.0.0.1:5600" + self.path, data=body, method="POST",
                                     headers={k: v for k, v in self.headers.items() if k.lower() in ("content-type", "user-agent", "origin", "referer")})
        try: r = urllib.request.urlopen(req, timeout=30); code, data, ct = r.status, r.read(), r.headers.get("Content-Type")
        except urllib.error.HTTPError as e: code, data, ct = e.code, e.read(), e.headers.get("Content-Type")
        except Exception: code, data, ct = 502, b'{"ok":false,"error":"admin-app not running"}', "application/json"
        self.send_response(code); self.send_header("Content-Type", ct or "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", 5510), functools.partial(H, directory=ROOT)).serve_forever()
