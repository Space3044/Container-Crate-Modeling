# Excel ULD 装载清单导出设计

## 背景

当前 XLSX 导出已有总体结果、ULD 数据、箱子数据和装箱坐标。
装箱坐标完整，但现场人员还需要在 Excel 中快速看到箱子大致位于 ULD 的哪个平面位置。

Excel 不适合复刻网页的交互式 3D。
本设计提供按 ULD 分组的装载清单和 `x/y` 俯视位置图。

## 目标

- 新增一个 `ULD 可视化` sheet。
- 每个 ULD 在该 sheet 内占一个区块。
- 每个 ULD 区块展示装载清单和一张俯视位置图。
- 装载清单统一使用 `长*宽*高*数量` 格式。
- 俯视位置图横向表示 ULD 长度方向 `x`，纵向表示 ULD 宽度方向 `y`。
- 俯视位置图按各摞的 anchor 点（footprint 左下角 minX、minY）离散化列和行。每一摞占据自己 anchor 位置的单一不合并单元格，同 anchor 的多摞在同一格内垂直堆叠内容。列头行头取各摞的 anchor 及其尺寸范围，坐标都是真实箱子位置。内容按 z 从下到上逐层书写。不使用单元格合并，消除合并覆盖导致 Excel 报错的风险。y 按降序排列（y 大的在上）。
- 保留现有 `装箱坐标` sheet 作为精确数据源。

## 非目标

- 不生成多个可视化 sheet。
- 不在 Excel 中实现交互式 3D。
- 不嵌入图片。
- 不表达高度方向的分层图。
- 不表达箱子遮挡顺序或点击交互。
- 不改变后端求解结果结构。

## Workbook 结构

导出结果包含：

```text
总体结果
ULD 明细
ULD 数据
箱子数据
已装箱类型
未装箱
ULD 可视化
装箱坐标
```

## ULD 可视化 Sheet

`ULD 可视化` sheet 内按 ULD 顺序排列区块。

每个 ULD 区块包含：

- ULD 标题行：ULD ID、类型、装载数、装载率。
- 横向装载清单：`装载清单` 后面依次写 `长*宽*高*数量`。
- `俯视位置图`：列头为 ULD `x` 坐标区间，行头为 ULD `y` 坐标区间，格子内写完整 `长*宽*高*数量`。

如果某个 ULD 没有已装箱，显示 `暂无已装箱`。

## 聚合规则

每个已装箱实例按实际放置尺寸聚合：

```text
key = placement.length + "*" + placement.width + "*" + placement.height
quantity = 相同 key 的实例数量
```

输出格式：

```text
长*宽*高*数量
```

该 sheet 不显示箱子代号、实例号和 `z` 分层标签。
需要精确定位时查看 `装箱坐标` sheet。

俯视位置图格子内按高度 `z` 从下到上逐层书写，同一层（相同 `z`）的箱子按 `长*宽*高` 聚合数量，每层一行 `长*宽*高*数量`，多层之间换行。

## 俯视位置图

俯视位置图按各摞的 anchor 点离散化列和行，形成网格。每一摞占据自己 anchor 位置的单一单元格（不合并）：

```text
横向 = ULD x 长度方向（向右为正）
纵向 = ULD y 宽度方向（向上为正，第一象限）
一摞 = 一个单元格，位置由其 anchor (minX, minY) 决定
格子内容 = 从下到上逐层写 长*宽*高*数量
单元格尺寸 = 同列摞的最大长度 × 同行摞的最大宽度
```

网格构建步骤：

1. 从所有摞中提取唯一的 anchorX（各摞的 minX）和 anchorY（各摞的 minY）
2. anchorX 按升序排列（从左到右），anchorY 按降序排列（y 大的在上）
3. 列宽 = 该列所有摞的最大长度；行高 = 该行所有摞的最大宽度
4. 表头：行头为 `y-y+宽`, 列头为 `x-x+长`
5. 每一摞在其 anchor 对应的单元格内写内容

同一 anchor 位置的多摞（真实足迹重叠）在同一单元格内用换行符分隔，按 z 从下到上书写每一层。每个箱子只在自己所在摞的单元格里出现一次。俯视位置图中的数量总和必须等于横向装载清单总和。由于不使用合并，消除了 Excel 合并矩形可能互相覆盖导致报错的风险。

## 数据流

现有导出流程保持：

```text
state.result + state.input
→ buildWorkbookSheets(result, input)
→ buildXlsxWorkbook(sheets)
→ downloadExcelWorkbook(...)
```

新增：

```text
buildUldVisualizationSheet(containers)
buildUldVisualizationSection(container)
placementSizeSummaries(placements)
buildTopViewRows(placements)
```

## 测试

更新 `tests/test_web_visualizer_assets.py`：

- 断言 workbook 包含 `ULD 可视化` sheet。
- 断言 `ULD 可视化` 包含 ULD 区块标题。
- 断言 `ULD 可视化` 横向展示 `长*宽*高*数量` 汇总。
- 断言 `ULD 可视化` 包含 `俯视位置图`。
- 断言俯视图列头由各摞的 anchorX 和宽度范围组成，行头由各摞的 anchorY 和长度范围组成，y 降序（y 大的在上）。
- 断言俯视图不使用合并单元格（merges 为空）。
- 断言每一摞占据自己 anchor 对应的单个单元格。
- 断言每个箱子只在自己所在摞的单元格里出现一次。
- 断言俯视图数量总和等于横向装载清单总和。
- 断言同一摞内容从下到上逐层书写 `长*宽*高*数量`，多层之间换行。
- 断言多行内容的行启用换行并加高行高。
- 断言 `ULD 可视化` 不包含箱子实例号。
- 断言现有 `装箱坐标` sheet 保留。

## 取舍

这个设计表达 `x/y` 平面位置，不表达高度层级和遮挡顺序。
精确三维定位继续交给网页交互和 `装箱坐标`。
