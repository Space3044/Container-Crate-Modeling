# ULD 装箱算法改进记录

本文记录当前 ULD 装箱算法的演进、实现位置和后续优化方向。

## 当前定位

当前算法是启发式装箱算法，不是数学严格最优解。

目标是在不引入重型求解器的前提下，快速得到稳定、可解释、可验证的较优装箱方案。核心实现位于：

```text
cargo_loading/profile_packer.py
```

相关回归测试位于：

```text
tests/test_profile_packer.py
tests/test_multi_container_packer.py
```

## 基础模型

ULD 使用三维坐标表示：

```text
x = ULD 长度方向
y = 截面宽度方向
z = 高度方向
```

ULD 的横截面使用 `y-z` 多边形描述，所以四边形、五边形等截面都可以统一处理。

箱子 `rotatable=true` 时只允许水平旋转，也就是长宽互换。高度始终保持输入值，不会把箱子倒置或侧翻。

每个箱子放置后会生成三个新候选点：

```text
(x + length, y, z)
(x, y + width, z)
(x, y, z + height)
```

后续箱子只在候选点上尝试放置，避免对连续空间做暴力搜索。

候选点会过滤掉已经落在已放箱子内部的旧点，避免无效低层点挤占候选点列表。否则重复箱子数量变大时，上层候选点可能被裁掉，导致明明还有上方空间却无法继续堆叠。

每个候选放置都会经过合法性校验：

```text
不超出 ULD 长度
不超出 y-z 截面多边形
不与已放置箱子重叠
如果 z > 0，底面支撑面积至少达到 80%
```

支撑面积只统计顶面高度刚好等于当前箱子底面 z 的下方箱子。不同高度但没有接触到箱底的箱子不会被算作支撑。

## 第一版：单排序贪心

最初算法按箱子体积从大到小排序。每个箱子遇到第一个可行候选点和长宽互换方向就立即放置。

优点是实现简单，速度快。

缺点是容易被局部选择影响。前面的箱子一旦占位不好，后面的可用空间会被切碎，导致总体装载量下降。

## 第二版：多排序策略试跑

第一次优化增加了多种箱子顺序。算法会对同一批箱子试跑多套排序策略：

```text
体积大优先
体积小优先
长度大优先
长度小优先
截面面积大优先
高度大优先
```

每种排序都会完整装一遍。最后根据目标函数选择最好的结果。

当前默认目标是：

```text
maximize_volume
```

评分优先级为：

```text
已装体积更大
已装数量更多
未装数量更少
```

如果目标设置为：

```text
maximize_count
```

评分优先级会变为：

```text
已装数量更多
已装体积更大
未装数量更少
```

这轮优化对应的测试是：

```text
test_pack_profile_tries_multiple_box_orders_to_improve_used_volume
```

该用例覆盖了旧算法只能装 1 个箱子、优化后能装 2 个箱子的情况。

## 第三版：Best-fit 候选位置评分

第二次优化把“遇到第一个可行位置就放”的逻辑改为 Best-fit。

现在每个箱子会枚举：

```text
所有候选点
所有允许长宽互换方向
```

然后对所有合法放置打分，选择评分最好的位置。

当前放置评分优先级为：

```text
放置后的整体包围体积更小
整体占用高度更低
整体占用宽度更小
整体占用长度更短
底面总支撑比例更高
单个主要支撑面的覆盖比例更高
贴墙或贴已有箱子的接触面更多
箱子自身 z 更低
箱子自身 y 更靠边
箱子自身 x 更靠前
```

这样做的目的，是让箱子尽量贴合已有结构，减少空间碎片。

这轮优化对应的测试是：

```text
test_pack_profile_scores_candidate_positions_and_orientations
```

该用例覆盖了旧算法只能装 8 个箱子、体积 366；优化后能装 9 个箱子、体积 414 的情况。

## 第四版：Beam Search 有限宽度搜索

第三次优化把单一路径贪心改成 Beam Search。

现在每放一个箱子时，算法不会只保留当前评分最高的一个中间方案，而是保留前 N 个中间方案继续扩展。

当前默认参数是：

```text
beam_width = 30
max_placement_branches = 20
```

含义是每一步最多保留 30 个中间装箱状态。每个状态对当前箱子最多取 20 个候选放置继续分支。

中间状态评分优先级和目标函数一致：

```text
maximize_volume:
已装体积更大
已装数量更多
未装数量更少
整体包围体积更小
占用高度、宽度、长度更小

maximize_count:
已装数量更多
已装体积更大
未装数量更少
整体包围体积更小
占用高度、宽度、长度更小
```

这样做的目的，是避免早期某个看似最优的放置把后续空间切碎。

这轮优化对应的测试是：

```text
test_pack_profile_keeps_multiple_partial_layouts_with_beam_search
```

该用例覆盖了 Best-fit 单路径只能装到体积 528，Beam Search 可以保留另一条中间路径并装到体积 576 的情况。

## 第五版：多 ULD 顺序试跑

第四次优化把多 ULD 从单一输入顺序改成多顺序试跑。

之前多 ULD 是按实例顺序逐个装载。这个方式稳定，但容易被输入顺序影响。前面的 ULD 可能抢走后面更适合装的箱子，导致总装载率下降。

如果多个 ULD 使用相同 ID，实例编号会连续生成：

```text
ULD-001
ULD-002
ULD-003
```

现在算法会对同一批 ULD 试跑多种顺序：

```text
输入顺序
可装箱种类少的 ULD 优先
ULD 体积大优先
ULD 体积小优先
截面面积大优先
截面面积小优先
长度大优先
长度小优先
```

每种 ULD 顺序都会完整装一遍。最后按目标函数选择总结果最好的方案。

相关测试是：

```text
test_pack_multi_profile_distributes_boxes_across_container_instances
test_pack_multi_profile_keeps_duplicate_uld_type_instance_ids_unique
test_pack_multi_profile_tries_multiple_uld_orders_to_improve_used_volume
test_pack_multi_profile_prioritizes_constrained_uld_before_flexible_uld
```

这版解决了输入顺序影响结果的问题，但仍然是“先定 ULD 顺序，再装当前 ULD”的分阶段策略。

## 第六版：多 ULD 全局 Beam Search

第五次优化把多 ULD 分配改成全局搜索。

现在算法不再先决定 ULD 顺序，而是在同一个搜索过程中同时选择：

```text
放哪个箱子
放进哪个 ULD
放在该 ULD 的哪个候选点
是否使用长宽互换方向
```

每个全局状态包含：

```text
所有 ULD 的已放箱子
所有 ULD 的候选点
剩余箱子数量
当前总装载体积和数量
```

每一步会从所有剩余箱型、所有 ULD、所有候选点中生成可行放置分支。然后按全局评分保留有限数量的状态继续扩展。

全局状态评分优先级为：

```text
maximize_volume:
总已装体积更大
总已装数量更多
未装数量更少
使用的 ULD 数量更少
已使用 ULD 的整体利用率更高
各 ULD 内部占用更紧凑

maximize_count:
总已装数量更多
总已装体积更大
未装数量更少
使用的 ULD 数量更少
已使用 ULD 的整体利用率更高
各 ULD 内部占用更紧凑
```

这轮优化对应的测试是：

```text
test_pack_multi_profile_uses_global_beam_search_to_keep_non_greedy_assignments
```

该用例覆盖了“当前 ULD 的局部最优选择会破坏全局最优”的情况。旧的多 ULD 顺序试跑只能装到体积 716，全局 Beam Search 可以装到体积 1000。

## 第七版：大规模搜索剪枝

第六次优化面向大量 ULD、大量箱型和大量箱子数量。

全局 Beam Search 如果每一步都尝试所有箱型、所有 ULD、所有候选点，分支数会快速膨胀。现在增加了几层剪枝和批量推进：

```text
每个状态只取 Top K 箱型
每个箱型只取 Top K 个可行 ULD
每个 ULD 只取有限个候选放置
同箱型连续可放时批量推进
搜索总步数加保护上限
```

当前默认参数是：

```text
max_global_box_type_candidates = 8
max_global_container_candidates = 12
max_global_branches_per_state = 80
max_batch_placements = 8
max_global_search_steps = 1000
```

当箱型数量或 ULD 数量变大时，算法会自动切到更激进的剪枝参数，减少 beam 宽度、候选箱型数和候选 ULD 数。

候选点不能剪得太狠。大规模模式会保留更宽的候选点池，避免上层堆叠位置被裁掉。数量变多时主要依靠同箱型批量推进控制运行时间。

候选点也不能只按 `z, y, x` 从低到高截断。大规模多箱型场景里，低层边角点数量会很快膨胀，如果只保留最底层的点，上层可堆叠位置会被挤掉。现在候选点裁剪会先保留一部分低层贴边点，再按高度层轮流保留候选点，让地板填充和上层堆叠同时保留。

箱型筛选会优先考虑：

```text
能放进的 ULD 更少
体积更大
剩余数量更多
最长边更长
```

这样做的目的，是让搜索优先处理更受限制、更影响总体利用率的箱型。

相关测试是：

```text
test_global_search_limits_candidate_box_types_for_large_type_sets
test_global_search_limits_candidate_containers_for_large_uld_sets
test_global_search_batches_repeated_box_placements_for_large_quantities
test_pack_multi_profile_keeps_layer_candidates_for_many_uld_and_box_types
```

这轮优化的目标不是提升小数据集的极限装载率，而是让大数据集不会被组合爆炸拖死。

新加入的大规模回归数据包含 20 个 ULD、25 个箱型、共 1000 个箱子。旧的候选点裁剪只能装入 905 个箱子；按高度层保留候选点后，可以装入 1000 个箱子，未装箱为 0，体积利用率不低于 58%。

## 第八版：多 ULD 成本优先

第七次优化补了一组更贴近现场的混合货物测试。该测试包含两个不同轮廓的 ULD，以及邮件托盘、电商纸箱、备件箱、高箱和超高箱。

旧评分在总装载体积相同的情况下，会倾向把货物分摊到多个 ULD，以换取利用率均衡。但现场里 ULD 本身有成本，所以同样能装下时，应优先少用 ULD。

现在全局评分在“总已装体积、总已装数量、未装数量”之后，会优先减少已使用 ULD 数量。只有使用 ULD 数量相同，才继续比较已使用 ULD 的整体利用率和内部紧凑度。

相关测试是：

```text
test_pack_multi_profile_handles_field_like_mixed_air_cargo_manifest
```

该用例中总体装载体积保持 4,950,000，25 个可装箱全部放入 ULD-A，ULD-B 保持空置。按已使用 ULD 计算，ULD-A 利用率约 43.96%。

## 第九版：优先填满已用 ULD 与剩余小箱补空

第八次优化面向大量 ULD、大量箱子时的两个问题：

```text
同类箱子容易过早分散到太多 ULD
主搜索结束后，已使用 ULD 内仍有小箱可补的碎片空间
```

现在选择 ULD 时会先检查已经使用的 ULD。只要已使用 ULD 还有合法位置，就优先继续往里面装；只有已使用 ULD 都放不下当前箱型时，才打开新的 ULD。

主搜索结束后，会对仍未装载的小箱执行一次补空流程。补空时会重新从已放箱子生成更完整的候选点，尽量把剩余小箱塞进已使用 ULD 的碎片空间，而不是马上依赖新增 ULD。

同时，堆叠评分增加了“主要支撑面覆盖比例”。如果两个旋转方向都合法，算法会优先选择更完整落在单个下方箱体上的方向，减少跨格摆放造成的空间切碎。

相关测试是：

```text
test_pack_multi_profile_packs_repeated_boxes_into_fewer_uld_before_opening_new_ones
test_pack_multi_profile_refills_fragmented_space_with_remaining_small_boxes
```

在 12 个 ULD、200 个同型箱的测试中，算法会先填满已使用 ULD，避免箱子被摊到过多容器。

在 12 个长方体 ULD、50 个大箱加 800 个小箱的测试中，算法可以完成全部 850 个箱子的装载，未装箱为 0。

## 当前算法总结

当前完整策略可以概括为：

```text
多排序策略试跑
+ Beam Search 保留多个中间方案
+ Best-fit 候选位置评分
+ 多 ULD 全局 Beam Search
+ 大规模 Top-K 剪枝和同箱型批量推进
+ 同等装载量下优先少用 ULD
+ 候选点按高度层保留，避免上层堆叠点被裁掉
+ 已用 ULD 优先与剩余小箱补空
+ 堆叠方向优先选择主要支撑面更完整的摆放
```

它比初版贪心更稳定，但由于 Beam Search 只保留有限数量的状态，仍然不是数学严格最优。

## 已知限制

当前算法仍有这些限制：

```text
候选点只来自已放箱子的右侧、后侧、上方
Beam Search 只保留有限数量的中间方案
beam_width、候选箱型数、候选 ULD 数、批量推进数量目前是代码常量
复杂场景仍可能错过更优组合
```

## 下一步优化方向

下一步可以把 `beam_width`、候选箱型数、候选 ULD 数和批量推进数量做成页面可配置项，让用户在速度和装载率之间自己取舍。

如果继续追求装载率，可以在全局 Beam Search 结果上加 LNS 大邻域搜索。思路是先得到一个较好方案，再反复移除一部分箱子并重新局部装载，直到达到时间预算。

如果后续需要数学意义上的严格最优解，再考虑 CP-SAT、整数规划或混合求解器方案。
