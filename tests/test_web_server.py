import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from cargo_loading.web_server import create_handler


class WebServerTests(unittest.TestCase):
    def test_post_pack_returns_profile_packing_result(self):
        server = self._start_server()
        try:
            payload = {
                "uld": {
                    "id": "ULD-001",
                    "length": 120,
                    "cross_section": [[0, 0], [100, 0], [100, 60], [70, 90], [0, 90]],
                },
                "boxes": [
                    {
                        "id": "BOX-A",
                        "length": 60,
                        "width": 50,
                        "height": 30,
                        "quantity": 2,
                        "rotatable": False,
                    }
                ],
            }

            response = self._post_json(server, "/api/pack", payload)

            self.assertEqual(response["result"]["loaded_count"], 2)
            self.assertEqual(response["result"]["loaded"], [{"box_id": "BOX-A", "quantity": 2}])
            self.assertEqual(response["result"]["unloaded_count"], 0)
            self.assertTrue(response["result"]["validation_passed"])
            self.assertEqual(response["result"]["placements"][0]["instance_id"], "BOX-A-001")
        finally:
            server.shutdown()
            server.server_close()

    def test_get_index_serves_visualizer_page(self):
        server = self._start_server()
        try:
            with urllib.request.urlopen(f"{self._base_url(server)}/", timeout=5) as response:
                content = response.read().decode("utf-8")

            self.assertIn("Multi ULD Profile Packing", content)
            self.assertIn("app.js", content)
        finally:
            server.shutdown()
            server.server_close()

    def test_post_pack_returns_bad_request_for_invalid_json(self):
        server = self._start_server()
        try:
            request = urllib.request.Request(
                f"{self._base_url(server)}/api/pack",
                data=b"{",
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=5)

            self.assertEqual(error.exception.code, 400)
            response = json.loads(error.exception.read().decode("utf-8"))
            self.assertIn("error", response)
        finally:
            server.shutdown()
            server.server_close()

    def _start_server(self):
        from http.server import ThreadingHTTPServer

        handler = create_handler(static_dir=Path("web"))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def _post_json(self, server, path: str, payload: dict):
        request = urllib.request.Request(
            f"{self._base_url(server)}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _base_url(self, server) -> str:
        host, port = server.server_address
        return f"http://{host}:{port}"


if __name__ == "__main__":
    unittest.main()
