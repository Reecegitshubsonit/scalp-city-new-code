#!/usr/bin/env python3
"""One-shot local form to set keys in .env. Binds 127.0.0.1 only, token-guarded, exits after one save.

Run from ~/scalp-city:  python3 keyform.py   then open the printed URL.
Values are written to .env (mode 600) and are never printed or logged.
"""
import html
import http.server
import os
import re
import secrets
import threading
import urllib.parse

FIELDS = [
    ("WEBULL_APP_KEY", "Webull App Key", True),
    ("WEBULL_APP_SECRET", "Webull App Secret", True),
    ("WEBULL_PAPER_ACCOUNT_NUMBER", "Webull paper account number", False),
]
TOKEN = secrets.token_urlsafe(16)
PORT = 8765


def write_env(values):
    text = open(".env").read() if os.path.exists(".env") else ""
    for name, value in values.items():
        line = f"{name}={value}"
        if re.search(rf"^{name}=.*$", text, flags=re.M):
            text = re.sub(rf"^{name}=.*$", lambda _: line, text, flags=re.M)
        else:
            text += ("" if text.endswith("\n") or not text else "\n") + line + "\n"
    with open(".env", "w") as handle:
        handle.write(text)
    os.chmod(".env", 0o600)


PAGE = """<!doctype html><meta charset=utf-8><title>scalp-city keys</title>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto;padding:0 16px">
<h2>Scalp City: set Webull paper keys</h2>
<p>Values go straight into <code>.env</code> on this machine. Leave a field empty to keep its current value.</p>
<form method=post action="/save?t={token}">{rows}
<button style="padding:8px 16px;margin-top:12px">Save</button></form></body>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body, code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _ok(self):
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("t") == [TOKEN]

    def do_GET(self):
        if not self._ok():
            return self._send("not found", 404)
        rows = "".join(
            f"<p><label>{html.escape(label)}<br><input name={name} type={'password' if secret else 'text'} "
            f"autocomplete=off style='width:100%;padding:6px'></label></p>"
            for name, label, secret in FIELDS
        )
        self._send(PAGE.format(token=TOKEN, rows=rows))

    def do_POST(self):
        if not self._ok():
            return self._send("not found", 404)
        size = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(size).decode())
        values, notes = {}, []
        for name, label, secret in FIELDS:
            value = (form.get(name, [""])[0]).strip()
            if not value:
                notes.append(f"{label}: unchanged")
                continue
            if name in ("WEBULL_APP_KEY", "WEBULL_APP_SECRET") and not re.fullmatch(r"[0-9a-fA-F]{32}", value):
                notes.append(f"{label}: saved, but not 32 hex characters (check it)")
            else:
                notes.append(f"{label}: saved")
            values[name] = value
        if values:
            write_env(values)
        self._send("<body style='font-family:sans-serif;max-width:520px;margin:40px auto'><h3>Done</h3><ul>"
                   + "".join(f"<li>{html.escape(n)}</li>" for n in notes) + "</ul>You can close this tab.")
        threading.Thread(target=self.server.shutdown, daemon=True).start()


if __name__ == "__main__":
    if not os.path.exists(".env"):
        raise SystemExit(".env not found; run from ~/scalp-city")
    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"http://127.0.0.1:{PORT}/?t={TOKEN}", flush=True)
    server.serve_forever()
