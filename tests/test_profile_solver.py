import json
import tempfile
import unittest
from pathlib import Path

from cargo_loading.profile_models import BoxPlacement, BoxSpec, ProfilePackingResult
from cargo_loading.profile_solver import merge_box_specs, packing_input_from_dict, packing_result_to_dict, solve_profile_file


class ProfileSolverTests(unittest.TestCase):
    def test_merge_box_specs_preserves_first_id_and_sums_rotatable_rows(self):
        merged = merge_box_specs(
            [
                BoxSpec(
                    id="BOX-A",
                    length=100,
                    width=80,
                    height=50,
                    quantity=2,
                    rotatable=True,
                    required_container_types=("Q7", "PGA"),
                ),
                BoxSpec(
                    id="BOX-B",
                    length=80,
                    width=100,
                    height=50,
                    quantity=3,
                    rotatable=True,
                    required_container_types=("PGA", "Q7"),
                ),
                BoxSpec(
                    id="BOX-C",
                    length=80,
                    width=100,
                    height=50,
                    quantity=1,
                    rotatable=False,
                    required_container_types=("Q7", "PGA"),
                ),
            ]
        )

        self.assertEqual([(box.id, box.quantity) for box in merged], [("BOX-A", 5), ("BOX-C", 1)])
        self.assertEqual((merged[0].length, merged[0].width), (100, 80))

    def test_packing_input_from_dict_merges_box_rows_before_building_problem(self):
        problem = packing_input_from_dict(
            {
                "uld": {
                    "id": "ULD-001",
                    "length": 120,
                    "cross_section": [[0, 0], [100, 0], [100, 60], [70, 90], [0, 90]],
                },
                "boxes": [
                    {"id": "BOX-A", "length": 60, "width": 50, "height": 30, "quantity": 2},
                    {"id": "BOX-B", "length": 60, "width": 50, "height": 30, "quantity": 3},
                ],
            }
        )

        self.assertEqual([(box.id, box.quantity) for box in problem.boxes], [("BOX-A", 5)])

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


    def test_merge_box_specs_merges_full_rotatable_rows_by_sorted_dimensions(self):
        # 全互换时三个尺寸的录入顺序不影响可选朝向，视为同一箱型
        merged = merge_box_specs(
            [
                BoxSpec(id="BOX-A", length=100, width=80, height=50, quantity=2, full_rotatable=True),
                BoxSpec(id="BOX-B", length=50, width=100, height=80, quantity=3, full_rotatable=True),
                BoxSpec(id="BOX-C", length=100, width=80, height=50, quantity=1),
            ]
        )

        self.assertEqual([(box.id, box.quantity) for box in merged], [("BOX-A", 5), ("BOX-C", 1)])
        self.assertTrue(merged[0].full_rotatable)
        self.assertFalse(merged[1].full_rotatable)

    def test_packing_input_from_dict_reads_full_rotatable_flag(self):
        data = {
            "containers": [{"id": "T", "length": 200, "quantity": 1, "cross_section": [[0, 0], [100, 0], [100, 100], [0, 100]]}],
            "boxes": [
                {"id": "BOX-A", "length": 50, "width": 50, "height": 150, "quantity": 1, "full_rotatable": True},
                {"id": "BOX-B", "length": 50, "width": 50, "height": 150, "quantity": 1},
            ],
        }

        problem = packing_input_from_dict(data)

        self.assertEqual([box.full_rotatable for box in problem.boxes], [True, False])


    def test_placement_dict_includes_height_swapped_flag(self):
        result = ProfilePackingResult(
            uld_id="T",
            loaded_count=1,
            unloaded_count=0,
            used_volume=1.0,
            cross_section_area=1.0,
            uld_volume=1.0,
            volume_utilization=1.0,
            placements=[
                BoxPlacement(box_id="B", instance_id="B-001", x=0, y=0, z=0, length=3, width=2, height=1, height_swapped=True),
                BoxPlacement(box_id="C", instance_id="C-001", x=0, y=0, z=0, length=1, width=2, height=3),
            ],
            unloaded=[],
            validation_passed=True,
        )

        data = packing_result_to_dict(result)

        self.assertEqual([item["height_swapped"] for item in data["placements"]], [True, False])


if __name__ == "__main__":
    unittest.main()
