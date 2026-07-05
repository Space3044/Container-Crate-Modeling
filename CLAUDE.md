# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

ULD（航空集装箱）装箱原型。给定若干个用 y-z 截面多边形描述的 ULD 和一批长方体箱子，用启发式算法求较优装箱方案，并在浏览器中可视化。纯 Python 标准库实现，无运行时第三方依赖（pyproject.toml 中 dependencies 为空），Python >= 3.12。

## 常用命令

```bash
# 运行全部测试（unittest，不是 pytest；必须在仓库根目录运行，部分测试读取相对路径文件）
python -m unittest discover -s tests

# 运行单个测试文件 / 单个用例
python -m unittest tests.test_profile_packer
python -m unittest tests.test_profile_packer.ProfilePackerTests.test_pack_profile_places_boxes_inside_five_sided_cross_section

# CLI 求解（输出 packing_result.json 及 SVG 预览到指定目录）
python -m cargo_loading.cli pack-profile --input data/profile_packing_input.json --output outputs/profile

# 启动浏览器可视化服务（默认 http://127.0.0.1:8000/）
python -m cargo_loading.cli serve-profile
# 或
python -m cargo_loading.web_server

# 桌面打包入口（PyInstaller 用，随机端口 + 自动开浏览器）
python launcher.py
```

Windows 下 venv 解释器位于 `.venv/Scripts/python.exe`。

## 架构

数据流：JSON 输入 → `profile_solver.packing_input_from_dict`（dict → dataclass）→ `profile_packer.pack_packing`（核心算法）→ result dataclass → `packing_result_to_dict`（dataclass → dict）→ CLI 文件输出或 HTTP JSON 响应。

`cargo_loading/` 各模块职责：

- `profile_models.py`：全部输入/输出 frozen dataclass 和校验。坐标约定：x = ULD 长度方向，y-z = 截面多边形平面。`search_mode` 取值 `fast | balanced | high_utilization`。输入分单 ULD（`ProfilePackingInput`，JSON 顶层有 `uld` 键）和多容器（`MultiContainerPackingInput`，顶层有 `containers` 键），由 `packing_input_from_dict` 自动分派。
- `profile_packer.py`：核心装箱算法（项目主体）。Beam Search + Maximal Spaces 空闲空间集合（`FreeSpace`，凸截面斜边滑入放置）+ 重复箱型层构建（混合朝向行组合整层分支）+ 立柱墙构建（同底面箱型族叠到截面顶、柱顶跨箱型压顶，仅非矩形截面启用）+ 多排序试跑 + 多 ULD 全局搜索 + Top-K 剪枝 + GRASP 随机重启（种子固定可复现，`_round_plan` 按模式和规模定轮数）。收尾阶段依次跑补空、定向腾挪（救回强约束箱型）和局部重排（含最差两 ULD 联合重装）。文件顶部的常量（beam 宽度、分支数、支撑率阈值等）是调参入口；`SearchLimits` 按 `search_mode` 切换三档参数。高装载率模式额外启用 multistart 排序变体和 0.7 支撑率。算法演进史和每版对应的回归测试见 `docs/algorithm-improvements.md`，改算法前先读它。
- `profile_geometry.py`：2D 凸多边形几何（凸性校验、点在多边形内、矩形 4 角点检验、斜边下可用 y 区间）。截面仅支持凸多边形，输入校验直接拒绝凹多边形。
- `profile_solver.py`：JSON ↔ dataclass 转换层和文件求解入口 `solve_profile_file`。
- `profile_visualizer.py`：单 ULD 结果的 SVG 渲染（截面预览、x 切片）。
- `web_server.py`：标准库 `http.server` 实现的 API + 静态文件服务。路由：`GET /api/sample`（返回 `data/profile_packing_input.json`）、`POST /api/pack`（求解）、`GET/POST /api/history`（历史记录，存到用户数据目录 `UldPacking/history.json`）。
- `cli.py`：argparse 入口，子命令 `pack-profile` 和 `serve-profile`。

`web/` 是无构建步骤的原生 HTML/CSS/JS 前端（`app.js` 约 2500 行），通过 `/api/pack` 提交问题并渲染投影视图、切片和选中详情。

## 约定

- `docs/packing-constraints.md` 是装箱边界条件和合法性规则的基准文件，算法实现可换、规则不变；改放置或校验逻辑前先对照它。
- 算法行为变更必须在 `docs/algorithm-improvements.md` 追加一节记录（动机、做法、对应测试、效果数字），现有十五版均如此。
- 测试是行为基准：每个算法改进都有对应回归测试锁定具体装载数量/体积，改动评分或剪枝逻辑后跑 `test_profile_packer.py` 和 `test_multi_container_packer.py` 确认没有回退。
- `tests/test_packaging_assets.py` 和 `tests/test_web_visualizer_assets.py` 用文本断言锁定 `launcher.py`、`.github/workflows/build.yml` 和 `web/` 资源的关键内容，改这些文件时同步更新断言。
- 发布构建走 GitHub Actions 手动触发（`workflow_dispatch`），PyInstaller 打包 Windows 和 macOS 产物，`launcher.py` 是打包入口（通过 `sys._MEIPASS` 定位 web/data 资源）。
- 代码全部使用 `from __future__ import annotations` 和 frozen dataclass 风格，注释和文档以中文为主。
