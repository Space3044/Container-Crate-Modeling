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

## 第十版：搜索模式配置

第九次优化把搜索强度做成三种模式，由页面输入并随 `/api/pack` 请求一起提交：

```text
fast：快速模式，收窄 beam、候选箱型、候选 ULD、候选位置和搜索步数，适合大量 ULD/箱子快速预览。
balanced：均衡模式，保持原有参数，作为默认值。
high_utilization：高装载率模式，放宽 beam、候选箱型、候选 ULD、候选位置、候选点和搜索步数，适合小中规模数据追求更高装载率。
```

模式字段为：

```text
search_mode = fast | balanced | high_utilization
```

相关测试是：

```text
test_global_search_limits_follow_search_mode
test_visualizer_page_has_projection_views_slice_control_and_selection_details
test_visualizer_script_contains_projection_and_selection_behaviors
```

## 第十一版：高装载率模式下的局部重排

第十次优化在高装载率模式收尾阶段加入了一轮 LNS 风格的局部重排，思路是先得到一个较好方案，再把装载率最低的 ULD 顶层箱子拆掉重塞：

```text
1. 仅在 search_mode == high_utilization 时启用
2. 按装载率升序挑出最差的非空 ULD
3. 把该 ULD 中处于最顶层（最大 z 层）的箱子拿出来，放回 remaining_counter
4. 走一遍 refill，看是否能在已用 ULD 中找到更紧凑的位置
5. 比对新旧全局分数，更优才接受，否则跳过该 ULD 试下一个
6. 最多重排 LOCAL_REARRANGE_MAX_PASSES 次（默认 3）
```

相关测试是：

```text
test_local_rearrange_is_noop_outside_high_utilization_mode
test_worst_container_indices_picks_lowest_utilization_and_skips_empties
test_ruin_and_recreate_strips_top_layer_and_keeps_bottom
test_pack_multi_profile_high_utilization_does_not_regress
```

## 第十二版：高装载率模式下的多排序起点与放宽支撑率

第十一次优化针对不规则截面 ULD（如 Q5 五边形截面）的装载率不足问题。在内部测试中 Q5 容器装 73 个箱子从 8 ULD 压到 7 ULD：

```text
1. 仅在 search_mode == high_utilization 时启用
2. pack_multi_profile 走 multistart：跑 4 个 box 评分变体取最优
   - variant 0：默认（数量多优先，maximize_count）/ 体积大优先（maximize_volume）
   - variant 1：纯体积大优先
   - variant 2：长边优先
   - variant 3：体积 × 数量加权优先
3. MIN_BOTTOM_SUPPORT_RATIO 按模式区分
   - fast / balanced：0.8（保守，物流业稳的标准）
   - high_utilization：0.7（允许 30% 悬空，行业常见值）
4. _placement_is_valid 和 validate_profile_packing 按 problem.search_mode 取阈值
5. _profile_input_for_container 传递 search_mode 到子问题，确保多 ULD 流程各阶段一致
```

相关测试是：

```text
test_min_support_ratio_relaxes_in_high_utilization_mode
test_pack_multi_profile_multistart_runs_variants_only_in_high_utilization
```

## 第十三版：Maximal Spaces 替换 Extreme Points 几何层

第十二次优化更换了几何装填器，这是边界条件规约（`docs/packing-constraints.md`）确认后的第一次大改。

旧几何层的候选位置只来自已放箱子的右侧、后侧、上方投影点（Extreme Points）。箱子之间夹出的空腔、斜边下方的空间不会出现在候选点列表里，搜索层再宽也看不到这些位置。这是 Q5 类不规则截面装载率天花板的来源。

新几何层维护每个容器的极大空闲长方体集合（Empty Maximal Spaces）：

```text
初始空间 = 截面包围盒 × ULD 长度，一个长方体
每放一个箱子，与其相交的空闲空间被切成最多 6 个子空间
removeContained：被其他空间包含的子空间丢弃，维持极大性不变量
候选位置 = 每个空闲空间的最小角，y 方向沿凸截面斜边滑入到第一个合法值
```

斜边处理依赖凸截面前提：箱子在高度区间 [z, z+h] 内的可用 y 区间，
由截面在 z 和 z+h 两个高度的切线区间取交集得到（`convex_y_interval`）。
候选 y 取空间左边界与多边形左边界的较大值，使箱子可以贴着斜边放置，
这是 Extreme Points 投影做不到的。

配套变更：

```text
截面多边形仅支持凸多边形，输入校验直接拒绝凹多边形
rectangle_inside_polygon 按凸前提简化为 4 角点判定
空闲空间数量上限沿用候选点裁剪策略：低层优先 + 按高度层轮流保留
SearchLimits.candidate_points 字段更名为 max_free_spaces
```

相关测试是：

```text
test_free_spaces_keep_stacking_space_above_placed_box
test_free_spaces_expose_cavity_above_lower_neighbor
```

全部 55 个既有回归测试不变通过，锁定的装载数字无一回退。基准对比（同机实测）：

```text
用例                        旧版                          新版
Q5×8，219 箱，high       2 ULD / 71.43% / 252 秒      2 ULD / 71.43% / 33 秒
混合货物 manifest，high   1 ULD / 52.28% / 21.6 秒     1 ULD / 52.28% / 2.3 秒
20 ULD / 25 箱型 / 1000 箱：
  fast                   11 ULD / 62.07% / 24.5 秒    10 ULD / 66.42% / 5.3 秒
  balanced               11 ULD / 62.07% / 36.9 秒    10 ULD / 66.42% / 7.9 秒
  high_utilization       10 ULD / 68.70% / 488 秒     9 ULD / 74.07% / 123 秒
```

速度提升 4-9 倍的原因：空闲空间集合天然不含无效位置，淘汰了大量
候选点 × 合法性检验的无效组合；fast 模式首次满足 10 秒预算。

## 第十四版：层构建、定向腾挪与 GRASP 随机重启

第十三次优化由一个现场反例驱动：PGA（600 长，五边形截面）装 27 个可旋转
BOX-A（114×95×102）加超长 BOX-B、BOX-C。手算最优是第一层 12 个（两行
95×114）、第二层 11 个（6+5 混排）、顶层放 B 和 C，且该摆法通过
`validate_profile_packing` 全量校验（支撑率 100%）。旧算法只能装 20-22 个。

诊断出三个结构性缺陷，全部出在搜索层：

```text
1. 放置评分按包围宽度偏好单一朝向，逐箱贪心永远到不了混合朝向的整层网格
2. 同箱型批量推进批内只取评分第一的候选，朝向多样性进不了 beam
3. 强约束箱型（只有一个 ULD 装得下的超长箱）在 beam 中途被大批量分支挤出，
   等收尾时空间已经碎了
```

对应三项修复：

```text
层构建（_layer_branch_in_container / _layer_layout_in_space）：
  对剩余数量 >= 4 的箱型，在每个空闲空间底面上枚举两种朝向的行组合
  （经典 pallet loading 行列混排），把箱数最多的整层作为一个复合分支。
  每个箱子放置前仍走 _placement_is_valid 独立校验。

批量推进保留朝向分支：
  候选截断时保证另一种朝向至少留一个（_diverse_orientation_candidates），
  每种朝向各生成一条批量推进分支，批内沿用种子朝向（preferred_orientation）。

收尾定向腾挪（_rescue_unloaded_boxes）：
  主搜索 + 补空之后，对静态可装却没装上的箱型，按破坏强度从小到大尝试
  先只拆顶层、再全腾空目标容器，先放该箱再回填，全局分数更优才接受。
  超长箱常见落点是层顶，拆顶层往往一步就救回。
```

搜索层在此之上接入 GRASP 随机化重启：

```text
每轮 = (box 排序变体, 随机种子)，种子固定可复现
候选选择从永远取第一改为受限候选列表（RCL，窗口 3）内随机挑
fast：1 轮确定性，速度不变
balanced：1 轮确定性 + 2 轮 GRASP
high_utilization：4 个确定性变体 + 3 轮 GRASP；
  大规模（>=12 容器或 >=20 箱型）缩到 2 个变体 + 1 轮 GRASP 保住分钟级预算
收尾阶段（补空、腾挪、局部重排）始终确定性
```

相关测试是：

```text
test_layer_building_reaches_hand_verified_pga_optimum
test_rescue_pass_recovers_constrained_long_box
```

效果（同机实测，对比第十三版）：

```text
用例                          第十三版                     第十四版
PGA 反例（手算最优 23+B+C）  20-22 个 A                   23 个 A + B + C（三档全中）
PGA 完整 5 ULD 场景          3 ULD，balanced 漏装 B       2 ULD，三档全装载
Q5×8，219 箱，high           2 ULD / 71.43% / 33 秒       1 ULD / 47.62%(满载) / 7 秒
20 ULD / 25 箱型 / 1000 箱：
  fast                       10 ULD / 66.42% / 5.3 秒     9 ULD / 74.07% / 7.4 秒
  balanced                   10 ULD / 66.42% / 7.9 秒     9 ULD / 74.07% / 31 秒
  high_utilization           9 ULD / 74.07% / 123 秒      9 ULD / 74.07% / 109 秒
```

Q5 用例的 73 个箱子总体积只有单个 Q5 的 47.62%，层构建后一个 ULD 全部装下，
少开一个 ULD。大规模用例 fast 档质量追平了原 high 档。

## 第十五版：立柱墙构建与高度带匹配

第十四次优化由另一个现场反例驱动：6 个 Q5（五边形截面，左侧 y<=120
全高 290，右侧斜边下最高只有 190）装 12 种箱型共 73 箱，箱子总体积
是 6 个 Q5 的 73.2%，算法装剩 4 箱。

诊断出的结构性缺陷是截面高度带错配：

```text
矮箱 A（63 高，数量 32）整层会铺满整个底面，三层叠到 189 之后，
全高带（290）上方剩下的 101 只有少数箱型能用；高箱（106-148 高）
被挤到没有可叠的空间，A 独占的 ULD 利用率天花板只有 69%。
手算的高效摆法是矮箱层让进斜边下的矮带（A 三层 189 正好贴住 190），
全高带留给高箱立柱（如 D+D+J = 101+101+88 = 290 正好顶满）。
```

对应改法是立柱墙复合分支（`_column_branch_in_container`）：

```text
同底面箱型族（底面尺寸完全一致，如 108×108 的 I/J/K/L 共 21 箱）
按高度组合叠立柱，沿 x 排成墙。每列用体积最大化枚举高度组合
（密度降序 + 乐观上界剪枝，`_max_volume_combo`），柱高上限由
斜边二分收敛（`_column_capacity`）。
柱顶允许一个跨箱型压顶箱（`_topper_orientation`，支撑率按模式
阈值校验，允许少量探出，如 108 宽的 J 压在 98 宽的 D 柱顶上）。
纯同族墙和带压顶墙各出一个分支，哪种更优交给 beam 全局评分裁决。
每个箱子放置前仍走 _placement_is_valid 独立校验，失败则整列截断。
```

三个配套约束控制成本和回归风险：

```text
矩形截面跳过立柱分支：没有高度带错配，整层构建已覆盖，
  无谓分支会挤占 beam（曾导致 850 箱回归用例少装 1 箱）
立柱墙只在该箱型评分最高的容器里试，空间扫描上限 16 个
  （large-fast 曾从 7.4 秒涨到 16.7 秒，收紧后回到 9.4 秒）
排序变体新增 variant 4（高箱优先），让高箱先占住全高带
```

收尾阶段新增最差两容器联合重装（`_repack_and_refill`）：单容器
腾挪只能在其余容器的缝隙里找位置，两个装载率都低的容器需要把
箱子合并重摆，所以允许重新打开被腾空的容器。

相关测试是：

```text
test_max_volume_combo_fills_column_height_exactly
test_column_building_improves_q5_height_band_case
```

效果（同机实测，对比第十四版）：

```text
用例                          第十四版                     第十五版
6×Q5 现场反例（73 箱）：
  fast                       62 箱 / 0.4 秒               67 箱 / 0.5 秒
  balanced                   67 箱 / 1.9 秒               68 箱 / 2.6 秒
  high_utilization           69 箱 / 11.3 秒              70 箱 / 30 秒
20 ULD / 25 箱型 / 1000 箱：
  fast                       9 ULD / 74.07% / 7.4 秒      8 ULD / 83.72% / 9.6 秒
  balanced                   9 ULD / 74.07% / 31 秒       8 ULD / 83.72% / 41 秒
  high_utilization           9 ULD / 74.07% / 109 秒      8 ULD / 80.35% / 219 秒
PGA 反例、Q5×8 等既有用例全部不回退（60 个回归测试通过）。
```

6×Q5 反例在高装载率档仍余 3 箱未装。该用例要求每个 ULD 平均
73.2% 利用率，而 A 独占 ULD 的天花板是 69%，需要每个 ULD 都
接近手算最优摆法才能全装下，是当前启发式的边界用例。

## 第十六版：人工指定 ULD 类型硬约束

动机：现场配载会有人为决策，部分箱型必须放入指定 ULD 类型。该要求是业务硬约束，不能被装载率评分、补空或局部重排覆盖；指定箱型应优先容纳，避免普通箱型先占用受限空间。

做法：

```text
BoxSpec 增加 required_container_types
MultiContainerPackingInput 校验指定的 ULD 类型必须存在
全局搜索候选容器按 required_container_types 过滤
全局搜索候选箱型排序优先处理带 required_container_types 的箱型
补空、救援、立柱墙压顶候选和结果校验统一遵守该约束
Web 表格增加“ULD 类型”列，逗号分隔多个类型 ID
Excel/HTML 导出的“箱子数据”保留该输入列
```

对应测试：

```text
test_pack_multi_profile_obeys_required_container_types
test_pack_multi_profile_prioritizes_required_container_type_boxes
test_multi_container_input_rejects_unknown_required_container_type
test_multi_container_input_from_dict_reads_required_container_types
test_required_container_types_parse_comma_separated_values
```

效果：未指定的箱型保持原有自动分配；指定后的箱型只会进入允许的 ULD 类型，并在搜索中优先尝试。若指定类型不存在，输入阶段直接报错，避免把人工录入错误静默解释成空间不足。

## 第十七版：Beam 体积进展多样性

动机：单个 Q7 装 7 个 `118×80×225` 大箱和 5 个小箱时，不指定
`required_container_types` 只能装入 11 箱；把所有大箱指定为 Q7 后却能装入
12 箱。单 Q7 下该约束没有改变任何可选容器，因此结果差异属于搜索剪枝问题。

诊断发现，立柱墙、层构建和重复箱型分支一次可以放入多个箱子，普通分支
通常只放一个。全局 beam 原本优先比较剩余箱数，多个小箱组成的复合分支会
在中间步骤压过单个大箱分支，把最终可以全部装入的路径提前裁掉。指定 Q7
后，`required_unloaded_count` 优先级意外保护了大箱路径，所以表现为“填写
冗余约束后结果变好”。

修复位于 `_select_global_beam_states`：

```text
先按原有全局评分选取 beam
额外找出满足人工约束前提下已装体积最大的进展状态
主 beam 和体积进展路径使用相互隔离的 frontier
主 beam 只从自身分支中继续选优，行为与增加体积路径前完全一致
体积路径使用独立 RNG 和一个补充槽，不能进入或替换主 beam
搜索轮数、合法性规则和复合分支保持不变
```

该机制不包含 Q7、箱子尺寸或特定箱型 ID 判断，处理的是所有“不同分支一次
放入箱数不同”导致的单一方向剪枝。立柱墙仍然保留，既有 Q5 高度带优化不回退。

对应测试：

```text
test_beam_keeps_large_box_path_when_small_column_branch_advances_more_boxes
test_volume_progress_path_uses_separate_frontier_from_standard_beam
```

效果：

```text
Q7 现场用例：未指定 / 指定 Q7 均从 11 箱提升到 12 箱，且全量合法性校验通过
相同尺寸合并为 quantity=7 时，三种搜索模式均可装入全部 12 箱
20 ULD / 25 箱型 / 1000 箱：仍装入 1000 箱，确定性布局哈希不变
大规模 balanced 本机时间约从 11 秒增至 13 秒，仍低于性能优化前的 18.49 秒
85 个回归测试全部通过
```

## 第十八版：计算前归并相同箱型

动机：同一物理箱型如果拆成多行录入，原有搜索会把每行当作独立箱型，导致箱型排序、批量铺层阈值和搜索分支发生变化。相同的货物数量不应因为录入行拆分而改变计算结果。

做法：

```text
按长、宽、高、长宽互换设置和指定 ULD 类型分组
长宽可互换时，长宽顺序归一后参与分组
数量相加，保留每组第一行的 ID 和其它字段
输入解析层与 pack_profile / pack_multi_profile 入口都归并，覆盖所有求解调用路径
Web 在计算前显示可归并提示，并将箱子表更新为实际参与计算的箱型行
发生多行归并时，beam 额外保留剩余体积更小的中间路径，避免合并大箱型后丢失可行解
```

不同 ULD 限制、不同长宽互换设置或不同高度的记录不会合并。合并后的装载清单、坐标实例和未装箱清单统一使用每组第一行 ID。

对应测试：

```text
test_merge_box_specs_preserves_first_id_and_sums_rotatable_rows
test_packing_input_from_dict_merges_box_rows_before_building_problem
test_pack_multi_profile_merges_equivalent_rows_before_calculation
```

## 第十九版：Beam 外廓多样性配额

动机：现场反例是单个 Q7（`306` 长，截面 `[[0,0],[240,0],[240,240],[120,291],[0,291]]`）装
12 箱（A 109×109×95 ×4、B 106×69×99 ×3、C 120×100×145 ×2、D 112×112×123、
E 110×110×146、F 124×100×154）。人工方案可以全部装入，三种搜索模式却都只装 11 箱。

逐步追踪确认候选生成没有问题：人工方案的 12 个位置全部出现在
`_placement_candidates` 的输出里，每步 rank 都是 0 或 1，远在 `placement_branches` 之内。
问题出在 beam 截断本身：

```text
单 ULD 路径每步放的是同一个箱子实例，各状态 used_volume / loaded_count 恒等，
_state_score 退化成只比 -bounding_volume
该用例的可行解要求高箱沿长度方向铺满 306，外廓 max_x=300 明显大于紧凑布局的 222~244
放第一个 A 开辟第二条 y 带时，目标路径在 81 个状态里排名第 80，被 beam_width=30 淘汰
beam 里 30 个名额只覆盖 29 种外廓中的 13 种，全是同一种紧凑形态的微小变体
多容器路径另有一层：分支可单放也可批量放，-unloaded_count 让批量分支凭放置数量
整批压过浅层分支，目标在深度 3 层内排名第 2，全局却排到第 223
```

做法是在 `_select_diverse_states` 里给 beam 增加多样性配额：

```text
先按原有分数取保底名额，行为与原实现一致
剩余名额按外廓 _bounding_extents 分组轮流补位，保证结构不同的布局都留下代表
多容器路径再按各容器放置数量分层，层内先按外廓交错，避免批量分支整批挤掉浅层分支
单 ULD 路径分数无区分度，保底名额留 1/3（PROFILE_BEAM_TOP_SCORE_QUOTA_DIVISOR）
多容器路径分数有真实区分度，多样性只占 1/3 补充名额（BEAM_DIVERSITY_QUOTA_DIVISOR）
合法性规则、候选生成、复合分支和搜索轮数均不变
```

配额比例是关键：多容器路径若让多样性占主导，第十五版的 Q5 高度带用例会从 67 箱回退到 66 箱。

对应测试：

```text
test_beam_diversity_keeps_spread_layout_in_sloped_q7（多容器路径）
test_beam_diversity_keeps_spread_layout_in_sloped_q7（单 ULD 路径）
```

效果：

```text
Q7 现场用例：单 ULD 与多容器两条路径、三种搜索模式均从 11 箱提升到 12 箱
装载率 0.6595 / 0.6977 提升到 0.7529，全量合法性校验通过
既有用例无回退：Q5 高度带仍 67 箱，97 个回归测试全部通过
20 ULD / 25 箱型 / 1000 箱（小箱全装场景）：仍装入 1000 箱，
  fast 本机 3.26 秒降至 2.01 秒，balanced 3.41 秒增至 3.83 秒
容器不足的大箱场景（同规模）：fast 161→159 箱、balanced 176→174 箱，
  活跃容器利用率 0.6717→0.6835，balanced 本机 30.33 秒增至 37.12 秒
```

## 第二十版：按箱型开启长宽高互换

动机：部分货物物流上允许侧翻或倒置，原规约固定高度方向，这类箱型无法利用
"立起来才装得进"的空间。业务方确认后按箱型放开全 6 朝向，默认关闭，
只有显式勾选的箱型参与全朝向计算，既有数据的结果不受影响。

做法：

```text
BoxSpec 增加 full_rotatable，默认 false，与 rotatable 独立录入
_orientation_options 在 full_rotatable 时返回三个尺寸的全部排列（去重后最多 6 种）
全互换已包含长宽互换，开启后 rotatable 取值不再影响可选朝向
归并键按三维排序后比较，长宽高顺序不同的同一箱型仍然合并
Web 箱子表格新增“长宽高互换”勾选列，默认不勾选，并入归并键与 Excel 导出
```

复合分支原本假设箱子高度恒为 `box.height`，全朝向下这个假设不再成立，一并修正：

```text
层构建按朝向高度分组，各高度分别求整层摆法后取最优，保证一层内同高、顶面平整
立柱墙按立柱底面反查每个箱型的朝向高度，没有该底面朝向的箱型不进柱
_topper_orientation 返回 (长, 宽, 高)，_max_volume_combo 按朝向高度而非 box.height 累计
剪枝用的 min_height 取各箱型所有朝向里的最小高度，避免误杀可行立柱
```

校验函数原本只查边界、截面、支撑和重叠，不检查放置尺寸是否为该箱型的合法朝向。
高度方向可变后这个缺口会放过实现 bug，因此补上朝向合法性检查：未开启
`full_rotatable` 的箱型若出现改变高度的放置，直接记为 `uses a disallowed orientation`。

对应测试：

```text
test_full_rotatable_allows_upright_orientation
test_full_rotatable_defaults_to_disabled
test_orientation_options_cover_all_six_permutations_when_full_rotatable
test_validate_rejects_height_swap_without_full_rotatable
test_merge_box_specs_merges_full_rotatable_rows_by_sorted_dimensions
test_packing_input_from_dict_reads_full_rotatable_flag
```

效果：

```text
默认关闭时全部既有回归测试结果不变
截面 100×100、箱子 50×50×150 的用例：关闭时 0 箱，开启后装入 2 箱并使用 (150,50,50) 朝向
朝向数量从最多 2 种增至最多 6 种，勾选箱型的候选枚举量相应增加
```

## 第二十一版：标出实际改变高度方向的放置

动机：开启 `full_rotatable` 只说明箱型允许侧翻或倒置，现场还需要知道最终方案中哪些具体箱子真的改变了高度方向。
如果只看输入勾选，无法在坐标表、可视化或导出文件中区分“允许互换”和“已经互换”。

做法：

```text
BoxPlacement 增加 height_swapped，默认 false，保持旧结果对象和旧输入兼容
生成最终单 ULD 结果时，按箱型核对放置高度；只有 full_rotatable 且高度不同才标记 true
JSON、主页面坐标表/悬停详情、HTML 报告、XLSX 坐标表和 SVG 预览同步显示提示
多 ULD 的每个容器结果复用同一标记逻辑，避免单 ULD 与多 ULD 展示不一致
```

对应测试：

```text
test_height_swapped_marks_only_placements_that_changed_height
test_height_swapped_stays_false_when_full_rotatable_box_keeps_input_height
test_pack_multi_profile_marks_height_swapped_placements
test_placement_dict_includes_height_swapped_flag
test_height_swapped_marker_survives_html_and_excel_exports
test_render_svg_titles_explain_height_swapped_placements
```

效果：

```text
不改变装箱搜索、评分或合法性规则；仅为最终放置增加可追溯的方向提示
全旋转箱子保留原始高度时不显示误报，未开启 full_rotatable 的箱型不会被标记
坐标、悬停、选中详情和导出结果均能识别实际需要长宽高互换的箱子
```

## 当前算法总结

当前完整策略可以概括为：

```text
多排序策略试跑
+ Beam Search 保留多个中间方案
+ Maximal Spaces 空闲空间集合 + Best-fit 候选位置评分
+ 凸截面斜边滑入放置
+ 重复箱型层构建：混合朝向行组合作为整层复合分支
+ 立柱墙构建：同底面箱型族叠到截面顶，柱顶跨箱型压顶，匹配截面高度带
+ 多 ULD 全局 Beam Search
+ 大规模 Top-K 剪枝和同箱型批量推进（批内保留朝向分支）
+ 同等装载量下优先少用 ULD
+ 空闲空间按高度层保留，避免上层堆叠空间被裁掉
+ 已用 ULD 优先与剩余小箱补空
+ 收尾定向腾挪：救回静态可装却被挤掉的强约束箱型
+ 堆叠方向优先选择主要支撑面更完整的摆放
+ 三种搜索模式，在速度和装载率之间切换
+ GRASP 随机化重启：balanced 与 high 档多轮取最优，种子固定可复现
+ 高装载率模式下对最差 ULD 顶层做局部重排，并对最差两 ULD 联合重装
+ 高装载率模式下 multistart 多 box 排序变体取最优（含高箱优先变体）
+ 高装载率模式下放宽底面支撑率到 0.7，允许更紧密堆叠
+ 人工指定 ULD 类型硬约束：指定箱型只允许进入 required_container_types 中的 ULD 类型，并优先容纳
+ Beam 体积进展多样性：复合分支推进多个小箱时，保留大体积箱子的长期可行路径
+ Beam 外廓多样性配额：装载量相同时按外廓分组轮流补位，多容器路径再按放置数量分层
+ 按箱型开启长宽高互换：勾选的箱型枚举全 6 朝向，默认关闭
```

它比初版贪心更稳定，但由于 Beam Search 只保留有限数量的状态，仍然不是数学严格最优。

## 已知限制

当前算法仍有这些限制：

```text
空闲空间数量有上限，超限后按高度层裁剪，可能丢失部分候选位置
Beam Search 只保留有限数量的中间方案
三种搜索模式仍是预设档位，不是自由参数调节
截面多边形仅支持凸多边形（边界规约确认的范围）
复杂场景仍可能错过更优组合
```

## 下一步优化方向

层构建和 GRASP 落地后，剩余的提升空间：

```text
BRKGA（偏置随机键遗传算法）：靠大量解码次数堆质量，需要业务接受更长运行时间
OR-Tools CP-SAT：小规模实例的严格最优档，用作启发式差距的标尺（引入第三方依赖，需决策）
GRASP 轮数和 RCL 窗口调参：当前 balanced 2 轮 / high 3 轮是保守值
```

短期内还可以做的小改进：

```text
放开箱子全 6 朝向旋转（已按箱型落地，默认关闭，见第二十版）
空闲空间裁剪策略调参（上限、低层配额比例）
层构建扩展到单 ULD 路径（pack_profile，目前只在多容器全局搜索生效）
```

如果后续需要数学意义上的严格最优解，再考虑 CP-SAT、整数规划或混合求解器方案。
