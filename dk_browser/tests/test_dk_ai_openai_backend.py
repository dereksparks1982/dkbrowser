"""Test local OpenAI-compatible inference without external network services."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json
import unittest

from dk_browser.ai.server import make_server


class FakeOpenAI(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/v1/models":
            return self.send_error(404)
        self.send_json({"data": [{"id": "test-russian-model"}]})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.send_error(404)
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert request["model"] == "test-russian-model"
        assert request["stream"] is False
        self.send_json({"choices": [{"message": {"content": "Привет из модели"}}]})


class OpenAIBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
        cls.ai = make_server(0, backend="openai", model_port=cls.fake.server_address[1])
        cls.threads = [Thread(target=server.serve_forever, daemon=True)
                       for server in (cls.fake, cls.ai)]
        for thread in cls.threads:
            thread.start()

    @classmethod
    def tearDownClass(cls):
        for instance in (cls.ai, cls.fake):
            instance.shutdown()
            instance.server_close()
        for thread in cls.threads:
            thread.join(timeout=2)

    def request(self, path, data=None, origin=None):
        headers = {}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if origin is not None:
            headers["Origin"] = origin
        req = Request(self.ai.origin + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers=headers)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_russian_chat(self):
        status, models = self.request("/api/models")
        self.assertEqual(status, 200)
        self.assertEqual(models["models"], ["test-russian-model"])
        payload = {"model":"test-russian-model",
                   "messages":[{"role":"user", "content":"Привет"}]}
        status, answer = self.request("/api/chat", payload, self.ai.origin)
        self.assertEqual(status, 200)
        self.assertEqual(answer["answer"], "Привет из модели")

    def test_reject_remote_origin_and_unknown_model(self):
        payload = {"model":"test-russian-model",
                   "messages":[{"role":"user", "content":"Hello"}]}
        status, _ = self.request("/api/chat", payload, "https://malicious.example")
        self.assertEqual(status, 403)
        payload["model"] = "missing"
        status, _ = self.request("/api/chat", payload, self.ai.origin)
        self.assertEqual(status, 400)
        with self.assertRaises(ValueError):
            make_server(0, backend="remote")


if __name__ == "__main__":
    unittest.main()
