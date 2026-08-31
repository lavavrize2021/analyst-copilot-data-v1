"""Analyst Copilot: dependency-free, evidence-first filing QA web application."""
from __future__ import annotations

import json
import os
import re
import threading
import traceback
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
from urllib.request import Request, urlopen

from copilot.index import FilingStore
from copilot.qa import answer_question

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv("COPILOT_DATA_DIR", ROOT / ".copilot_data"))
STORE = FilingStore(DATA)


class Handler(BaseHTTPRequestHandler):
    server_version = "AnalystCopilot/1.0"

    def log_message(self, fmt, *args):
        print(fmt % args)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "static" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)
        elif self.path == "/api/filings":
            self.send_json({"filings": STORE.list()})
        elif self.path.startswith("/api/status/"):
            self.send_json(STORE.status(self.path.rsplit("/", 1)[-1]))
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            if self.path == "/api/ask":
                n = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(n))
                self.send_json(answer_question(STORE, data.get("filing_id", ""), data.get("question", "")))
                return
            if self.path == "/api/upload":
                length = int(self.headers.get("Content-Length", "0"))
                if length > 82 * 1024 * 1024: raise ValueError("File exceeds the 80 MB limit")
                message = BytesParser(policy=default).parsebytes(
                    b"Content-Type: " + self.headers.get("Content-Type", "").encode() + b"\r\n\r\n" + self.rfile.read(length))
                item = next((part for part in message.iter_parts() if part.get_param("name", header="content-disposition") == "file"), None)
                if item is None: raise ValueError("No file was uploaded")
                raw = item.get_payload(decode=True)
                if len(raw) > 80 * 1024 * 1024: raise ValueError("File exceeds the 80 MB limit")
                job = STORE.begin(item.get_filename() or "filing.htm")
                threading.Thread(target=STORE.process, args=(job, raw), daemon=True).start()
                self.send_json({"job_id": job}, 202); return
            self.send_error(404)
        except (ValueError, KeyError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception:
            traceback.print_exc(); self.send_json({"error": "Internal error"}, 500)


if __name__ == "__main__":
    host, port = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", "8000"))
    print(f"Analyst Copilot running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
