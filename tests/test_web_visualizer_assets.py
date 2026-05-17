import unittest
from pathlib import Path


class WebVisualizerAssetsTests(unittest.TestCase):
    def test_visualizer_page_has_projection_views_slice_control_and_selection_details(self):
        html = Path("web/index.html").read_text(encoding="utf-8")

        for expected_id in [
            "containerTableBody",
            "addContainerButton",
            "containerSelector",
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
        self.assertIn("添加 ULD", html)
        self.assertIn("当前 ULD", html)
        self.assertIn("选择要查看的 ULD 实例", html)
        self.assertIn("<th>ID</th>", html)
        self.assertNotIn("<th>类型</th>", html)
        self.assertNotIn("容器", html)

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
            "readJsonResponse",
            "addContainerRow",
            "readContainersFromForm",
            "renderContainerSelector",
            "selectContainer",
            "normalizeInput",
            "expandContainerSpecs",
            "getActiveResult",
            "getActiveProfileInput",
            "renderActiveContainerDetails",
            "renderUnloadedList",
        ]:
            self.assertIn(f"function {expected_function}", script)
        self.assertIn("containers:", script)
        self.assertIn("containerSelector.addEventListener", script)
        self.assertNotIn("uldIdInput", script)
        self.assertNotIn("uldLengthInput", script)
        self.assertNotIn("crossSectionInput", script)
        self.assertNotIn("容器", script)
        self.assertIn("ULD ID", script)
        self.assertIn("缺少 ID", script)
        self.assertNotIn("ULD 类型", script)
        self.assertNotIn("缺少类型", script)
        self.assertIn("AXIS_EXTENSION_FACTOR", script)
        self.assertIn("dimensions.length * AXIS_EXTENSION_FACTOR", script)


if __name__ == "__main__":
    unittest.main()
