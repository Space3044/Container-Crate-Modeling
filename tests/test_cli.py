import json
import tempfile
import unittest
from pathlib import Path

from cargo_loading.cli import main


class CLITests(unittest.TestCase):
    def test_cli_pack_profile_writes_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            output_dir = root / "outputs"
            input_path.write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )

            exit_code = main(["pack-profile", "--input", str(input_path), "--output", str(output_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "packing_result.json").exists())

    def test_cli_serve_profile_uses_web_server_runner(self):
        calls = []

        exit_code = main(
            ["serve-profile", "--host", "0.0.0.0", "--port", "8765", "--static-dir", "web"],
            server_runner=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [{"host": "0.0.0.0", "port": 8765, "static_dir": "web"}])


if __name__ == "__main__":
    unittest.main()
