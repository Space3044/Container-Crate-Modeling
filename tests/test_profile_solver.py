import json
import tempfile
import unittest
from pathlib import Path

from cargo_loading.profile_solver import solve_profile_file


class ProfileSolverTests(unittest.TestCase):
    def test_solve_profile_file_writes_packing_result(self):
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

            result = solve_profile_file(input_path, output_dir)

            result_path = output_dir / "packing_result.json"
            preview_path = output_dir / "packing_preview.svg"
            slice_path = output_dir / "packing_x_slices.svg"
            self.assertTrue(result_path.exists())
            self.assertTrue(preview_path.exists())
            self.assertTrue(slice_path.exists())
            saved = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["uld_id"], "ULD-001")
            self.assertEqual(saved["loaded_count"], 2)
            self.assertEqual(saved["loaded"], [{"box_id": "BOX-A", "quantity": 2}])
            self.assertTrue(saved["validation_passed"])
            self.assertEqual(result.loaded_count, 2)


if __name__ == "__main__":
    unittest.main()
