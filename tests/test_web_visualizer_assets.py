import unittest
from pathlib import Path


class WebVisualizerAssetsTests(unittest.TestCase):
    def test_visualizer_page_has_projection_views_slice_control_and_selection_details(self):
        html = Path("web/index.html").read_text(encoding="utf-8")

        for expected_id in [
            "topViewCanvas",
            "sideViewCanvas",
            "sectionViewCanvas",
            "sliceSlider",
            "sliceValue",
            "loadedList",
            "selectedBoxDetails",
            "isometricViewButton",
            "topViewButton",
            "sideViewButton",
            "sectionViewButton",
        ]:
            self.assertIn(f'id="{expected_id}"', html)
        self.assertIn("只改变截面查看，不改变装箱结果", html)
        self.assertIn("x 从 ULD 前端沿长度方向量起", html)

    def test_visualizer_script_contains_projection_and_selection_behaviors(self):
        script = Path("web/app.js").read_text(encoding="utf-8")

        for expected_function in [
            "drawProjectionViews",
            "drawTopView",
            "drawSideView",
            "drawSectionView",
            "selectPlacement",
            "drawAxes",
            "setCameraView",
            "renderLoadedList",
        ]:
            self.assertIn(f"function {expected_function}", script)
        self.assertIn("AXIS_EXTENSION_FACTOR", script)
        self.assertIn("dimensions.length * AXIS_EXTENSION_FACTOR", script)


if __name__ == "__main__":
    unittest.main()
