import json
import tempfile
import unittest
from pathlib import Path

from cargo_loading.profile_solver import solve_profile_file


class MultiContainerSolverTests(unittest.TestCase):
    def test_solve_profile_file_writes_multi_container_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            output_dir = root / "outputs"
            input_path.write_text(
                json.dumps(
                    {
                        "containers": [
                            {
                                "id": "RECT",
                                "length": 60,
                                "cross_section": [[0, 0], [50, 0], [50, 50], [0, 50]],
                                "quantity": 2,
                            }
                        ],
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

            result = solve_profile_file(input_path, output_dir)

            saved = json.loads((output_dir / "packing_result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["loaded_count"], 2)
            self.assertEqual(saved["loaded"], [{"box_id": "BOX-A", "quantity": 2}])
            self.assertEqual([container["container_id"] for container in saved["containers"]], ["RECT-001", "RECT-002"])
            self.assertEqual(result.loaded_count, 2)


if __name__ == "__main__":
    unittest.main()
