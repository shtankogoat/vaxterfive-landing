"""Локальный dev-сервер: как nginx — /privacy → /privacy/, свои страницы ошибок. Запуск: python catalog-src/serve.py"""
import http.server, os, functools
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
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", 5510), functools.partial(H, directory=ROOT)).serve_forever()
