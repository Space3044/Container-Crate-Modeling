import unittest
import importlib.util
from pathlib import Path


class PackagingAssetsTests(unittest.TestCase):
    def test_manual_github_action_builds_windows_and_macos_artifacts(self):
        workflow = Path(".github/workflows/build.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("runs-on: macos-latest", workflow)
        self.assertIn('--add-data "web;web"', workflow)
        self.assertIn('--add-data "data;data"', workflow)
        self.assertIn('--add-data "web:web"', workflow)
        self.assertIn('--add-data "data:data"', workflow)
        self.assertIn("launcher.py", workflow)
        self.assertIn("UldPacking-windows", workflow)
        self.assertIn("UldPacking-mac", workflow)

    def test_launcher_opens_local_visualizer_server(self):
        launcher = Path("launcher.py").read_text(encoding="utf-8")

        self.assertIn("open_browser_when_started", launcher)
        self.assertIn("port=0", launcher)
        self.assertNotIn("PORT = 8000", launcher)
        self.assertNotIn("http://127.0.0.1:8000/", launcher)
        self.assertIn("run_server", launcher)
        self.assertIn('resource_path("web")', launcher)
        self.assertIn("multiprocessing.freeze_support()", launcher)

    def test_launcher_builds_browser_url_from_actual_server_port(self):
        launcher = self._load_launcher()

        self.assertEqual(launcher.build_url("127.0.0.1", 54321), "http://127.0.0.1:54321/")

    def test_web_server_can_report_automatically_assigned_port(self):
        server = Path("cargo_loading/web_server.py").read_text(encoding="utf-8")

        self.assertIn("on_started", server)
        self.assertIn("server.server_address", server)
        self.assertIn("actual_port", server)

    def _load_launcher(self):
        spec = importlib.util.spec_from_file_location("launcher", Path("launcher.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


if __name__ == "__main__":
    unittest.main()
