## 2026-07-20 大规模装箱候选评估重复计算优化

### 现象与影响

3500 箱在 balanced 模式运行超过 20 分钟。仓库 1000 箱基准运行 18.49 秒，候选位置生成、支撑计算、接触面计算和状态评分占用主要 CPU 时间。

### Root cause

候选位置校验和评分会多次扫描同一容器的全部 placements；截面几何结果被重复计算；beam 状态评分反复汇总已装体积和包围尺寸；refill 阶段重新构建已经存在的 free spaces。

### 最终 solution

为截面区间和矩形边界检查增加有界缓存；为候选评估建立按坐标面和顶部高度组织的精确索引；一次候选评估复用碰撞、支撑和接触面数据；在 ContainerState 中增量维护容器体积、已装体积和包围尺寸；refill 复用现有 free_spaces。

搜索轮数、beam 宽度、候选数量、评分规则、支撑率和合法性约束均保持不变。

### Validation method 和结果

执行 `python -m unittest discover -s tests`，84 个测试全部通过。

1000 箱基准：

- balanced：18.49 秒降至 11.07 秒
- fast：3.08 秒降至 2.03 秒
- loaded_count、unloaded_count、使用 ULD 数、used_volume 和 utilization 完全一致
- 确定性布局 SHA-256 优化前后均为 `af7ad0d5d9b15bf7de3dd83d4aff19bf342b1f66518fbb1b45abde766e2992c0`

### 可复用经验或预防措施

性能优化前先使用 profiler 确认热路径。对启发式算法进行等价优化时，除汇总指标外还应比较完整布局哈希，防止浮点顺序或候选排序变化导致隐性质量变化。对纯几何函数使用有界缓存，对重复空间关系查询建立精确索引。
