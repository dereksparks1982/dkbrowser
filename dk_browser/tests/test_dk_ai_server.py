"""Local DK AI HTTP boundary tests with fake loopback Ollama.

Run: python3 -m unittest discover -s dk_browser/tests
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dk_browser.ai.server import make_server


class FakeModel(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path != "/api/tags":
            self.send_error(404)
            return
        body = json.dumps({"models":[{"name":"test-local:latest"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        assert request["stream"] is False
        assert request["model"] == "test-local:latest"
        body = json.dumps({"message":{"content":"Тестовый ответ"}}).encode()
        self.send_response(200)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DKAILocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1",0), FakeModel)
        cls.api = make_server(0, cls.fake.server_address[1])
        cls.threads = [Thread(target=server.serve_forever,daemon=True)
                       for server in (cls.fake, cls.api)]
        for thread in cls.threads:
            thread.start()
        cls.origin = cls.api.origin

    @classmethod
    def tearDownClass(cls):
        for server in (cls.api,cls.fake):
            server.shutdown()
            server.server_close()
        for thread in cls.threads:
            thread.join(timeout=2)

    def fetch(self, path, *, method="GET", payload=None, origin=None, host=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if origin is not None:
            headers["Origin"] = origin
        if host is not None:
            headers["Host"] = host
        request = Request(self.origin + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, exc.read()

    def test_interface_is_local_and_secured(self):
        status, data = self.fetch("/")
        self.assertEqual(status,200)
        self.assertIn(b"/app.js",data)
        self.assertEqual(self.api.server_address[0],"127.0.0.1")
        status, _ = self.fetch("/api/models",host="evil.example")
        self.assertEqual(status,403)
        status, _ = self.fetch("/../server.py")
        self.assertEqual(status,404)

    def test_models_and_russian_response(self):
        status, raw = self.fetch("/api/models")
        self.assertEqual(status,200)
        self.assertEqual(json.loads(raw)["models"],["test-local:latest"])
        payload={"model":"test-local:latest",
                 "messages":[{"role":"user","content":"Привет"}]}
        status, raw = self.fetch("/api/chat",method="POST",
                                 payload=payload,origin=self.origin)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(raw)["answer"],"Тестовый ответ")

    def test_reject_other_site_and_uninstalled_models(self):
        payload={"model":"test-local:latest",
                 "messages":[{"role":"user","content":"Test"}]}
        for other in (None,"https://evil.example"):
            status, _ = self.fetch("/api/chat",method="POST",
                                   payload=payload,origin=other)
            self.assertEqual(status,403)
        payload["model"] = "not-installed"
        status, _ = self.fetch("/api/chat",method="POST",
                               payload=payload,origin=self.origin)
        self.assertEqual(status,400)
        payload["model"] = "test-local:latest"
        payload["messages"][0]["role"] = "system"
        status, _ = self.fetch("/api/chat",method="POST",
                               payload=payload,origin=self.origin)
        self.assertEqual(status,400)


if __name__ == "__main__":
    unittest.main()
