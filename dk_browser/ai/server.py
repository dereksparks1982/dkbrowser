"""Optional DK AI local-only assistant server.

Standard library only. Serves a same-origin browser UI and proxies a fixed
Ollama endpoint on 127.0.0.1. Does not auto-download models or send cloud data.
No tool use or browser automation is exposed to the model.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import urllib.error
import urllib.request
import webbrowser

STATIC = Path(__file__).resolve().parent
# Only allow explicitly listed static files; never accept a client file path.
ASSETS = STATIC.parents[1] / "assets" / "images"
FILES = {
    "/": (STATIC / "index.html", "text/html; charset=utf-8"),
    "/index.html": (STATIC / "index.html", "text/html; charset=utf-8"),
    "/app.js": (STATIC / "app.js", "text/javascript; charset=utf-8"),
    "/style.css": (STATIC / "style.css", "text/css; charset=utf-8"),
    "/assets/dk-icon-en.png": (
        ASSETS / "DK Browser Imperial Icon.png", "image/png"),
    "/assets/dk-icon-ru.png": (
        ASSETS / "DK Browser Russian Imperial Icon.png", "image/png"),
}
MAX_REQUEST = 64 * 1024
MAX_REPLY = 2 * 1024 * 1024
MAX_MESSAGES = 30
MAX_MESSAGE_LENGTH = 10000


class BackendError(Exception):
    pass


class Handler(BaseHTTPRequestHandler):
    server_version = "DKAI/0.1"

    def log_message(self, format, *args):
        # Never print request/response bodies or private chat content.
        super().log_message(format, *args)

    def _secure_host(self):
        return self.headers.get("Host", "") == self.server.expected_host

    def _send(self, status, data: bytes, kind="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
                         "base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status, payload):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _backend(self, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.server.backend_base}{path}", data=body,
            headers={"Content-Type": "application/json"} if body else {},
            method="POST" if body else "GET")
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read(MAX_REPLY + 1)
            if len(raw) > MAX_REPLY:
                raise BackendError("Model response exceeds the safety limit.")
            return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise BackendError("Local AI model service is unavailable or returned invalid data.") from exc

    def _models(self):
        openai = self.server.backend == "openai"
        result = self._backend("/v1/models" if openai else "/api/tags")
        key = "data" if openai else "models"
        field = "id" if openai else "name"
        if not isinstance(result, dict) or not isinstance(result.get(key), list):
            raise BackendError("The local model list is invalid.")
        names = []
        for entry in result[key][:100]:
            if isinstance(entry, dict) and isinstance(entry.get(field), str):
                name = entry[field]
                if 0 < len(name) < 200:
                    names.append(name)
        return names

    def do_GET(self):
        if not self._secure_host():
            return self._json(403, {"error": "Unexpected host."})
        path = self.path.split("?", 1)[0]
        if path == "/api/models":
            try:
                return self._json(200, {"models": self._models()})
            except BackendError as exc:
                return self._json(503, {"error": str(exc)})
        if path not in FILES:
            return self._json(404, {"error": "Not found."})
        file_path, kind = FILES[path]
        try:
            contents = file_path.read_bytes()
        except OSError:
            return self._json(404, {"error": "Asset is unavailable."})
        return self._send(200, contents, kind)

    def do_POST(self):
        if not self._secure_host():
            return self._json(403, {"error": "Unexpected host."})
        if self.headers.get("Origin") != self.server.origin:
            return self._json(403, {"error": "Cross-origin requests are blocked."})
        if self.path != "/api/chat":
            return self._json(404, {"error": "Not found."})
        if self.headers.get_content_type() != "application/json":
            return self._json(415, {"error": "JSON content type required."})
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            return self._json(400, {"error": "Invalid request length."})
        if not (0 < size <= MAX_REQUEST):
            return self._json(413, {"error": "Request is too large."})
        try:
            data = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "Invalid JSON."})
        if not isinstance(data, dict):
            return self._json(400, {"error": "Invalid request."})
        model, messages = data.get("model"), data.get("messages")
        if not isinstance(model, str) or not isinstance(messages, list) or not (1 <= len(messages) <= MAX_MESSAGES):
            return self._json(400, {"error": "A model and messages are required."})
        if any(not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
               or not isinstance(item.get("content"), str)
               or not (0 < len(item["content"]) <= MAX_MESSAGE_LENGTH) for item in messages):
            return self._json(400, {"error": "Invalid chat messages."})
        if messages[-1]["role"] != "user":
            return self._json(400, {"error": "The last message must be from the user."})
        try:
            if model not in self._models():
                return self._json(400, {"error": "Choose an installed local model."})
            if self.server.backend == "openai":
                response = self._backend("/v1/chat/completions", {
                    "model": model, "messages": messages, "stream": False,
                    "max_tokens": 2048
                })
            else:
                response = self._backend("/api/chat", {
                    "model": model, "messages": messages, "stream": False,
                    "options": {"num_predict": 2048}
                })
        except BackendError as exc:
            return self._json(503, {"error": str(exc)})
        if self.server.backend == "openai":
            choices = response.get("choices") if isinstance(response, dict) else None
            choice = choices[0] if isinstance(choices, list) and choices else None
            message = choice.get("message") if isinstance(choice, dict) else None
        else:
            message = response.get("message") if isinstance(response, dict) else None
        answer = message.get("content") if isinstance(message, dict) else None
        if not isinstance(answer, str):
            return self._json(502, {"error": "The model did not return a text answer."})
        return self._json(200, {"answer": answer[:MAX_MESSAGE_LENGTH]})


def make_server(port=8766, ollama_port=11434, backend="ollama",
                model_port=8000):
    if backend not in ("ollama", "openai"):
        raise ValueError("Unsupported local AI backend.")
    if not (0 <= port <= 65535 and 1 <= ollama_port <= 65535
            and 1 <= model_port <= 65535):
        raise ValueError("Invalid local network port.")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    listen_port = httpd.server_address[1]
    httpd.expected_host = f"127.0.0.1:{listen_port}"
    httpd.origin = f"http://{httpd.expected_host}"
    httpd.backend = backend
    # Fixed to loopback. No arbitrary URL, external host, or token accepted.
    backend_port = ollama_port if backend == "ollama" else model_port
    httpd.backend_base = f"http://127.0.0.1:{backend_port}"
    return httpd


def main():
    parser = argparse.ArgumentParser(description="Run DK AI locally; no account or cloud required.")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--ollama-port", type=int, default=11434)
    parser.add_argument("--backend", choices=("ollama", "openai"),
                        default="ollama", help="Choose a local AI model server.")
    parser.add_argument("--model-port", type=int, default=8000,
                        help="Loopback port for an OpenAI-compatible model server.")
    parser.add_argument("--open", action="store_true", help="Open the local UI in your browser.")
    args = parser.parse_args()
    with make_server(args.port, args.ollama_port, args.backend, args.model_port) as httpd:
        print(f"DK AI local assistant: {httpd.origin}")
        if args.open:
            webbrowser.open(httpd.origin)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDK AI stopped.")


if __name__ == "__main__":
    main()
