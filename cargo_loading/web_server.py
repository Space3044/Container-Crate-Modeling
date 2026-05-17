from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cargo_loading.profile_packer import pack_profile
from cargo_loading.profile_solver import profile_input_from_dict, profile_result_to_dict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATIC_DIR = PROJECT_ROOT / "web"
DEFAULT_SAMPLE_PATH = PROJECT_ROOT / "data" / "profile_packing_input.json"


def create_handler(
    static_dir: str | Path = DEFAULT_STATIC_DIR,
    sample_path: str | Path = DEFAULT_SAMPLE_PATH,
) -> type[BaseHTTPRequestHandler]:
    static_root = Path(static_dir).resolve()
    sample_file = Path(sample_path).resolve()

    class ProfilePackingRequestHandler(BaseHTTPRequestHandler):
        server_version = "ProfilePackingHTTP/0.1"

        def do_GET(self) -> None:
            if self.path in {"/", "/index.html"}:
                self._send_static_file(static_root / "index.html")
                return
            if self.path == "/api/sample":
                self._send_json(json.loads(sample_file.read_text(encoding="utf-8")))
                return
            if self.path.startswith("/api/"):
                self._send_json({"error": "unknown api route"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_static_file(static_root / self.path.lstrip("/"))

        def do_POST(self) -> None:
            if self.path != "/api/pack":
                self._send_json({"error": "unknown api route"}, status=HTTPStatus.NOT_FOUND)
                return

            try:
                payload = self._read_json_body()
                problem = profile_input_from_dict(payload)
                result = pack_profile(problem)
            except Exception as error:
                self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
                return

            self._send_json({"result": profile_result_to_dict(result)})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw_body)
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static_file(self, file_path: Path) -> None:
            resolved_path = file_path.resolve()
            if not _is_inside(resolved_path, static_root) or not resolved_path.is_file():
                self._send_json({"error": "file not found"}, status=HTTPStatus.NOT_FOUND)
                return

            body = resolved_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", _content_type(resolved_path))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ProfilePackingRequestHandler


def run_server(host: str = "127.0.0.1", port: int = 8000, static_dir: str | Path = DEFAULT_STATIC_DIR) -> None:
    handler = create_handler(static_dir=static_dir)
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"ULD packing visualizer running at http://{host}:{port}/")
        server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the single ULD packing visualizer web page.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--static-dir", default=str(DEFAULT_STATIC_DIR))
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port, static_dir=args.static_dir)
    return 0


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "text/javascript; charset=utf-8"
    if suffix == ".svg":
        return "image/svg+xml"
    return "application/octet-stream"


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
