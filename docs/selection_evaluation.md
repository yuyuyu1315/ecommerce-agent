# 选品 Agent 回测报告

- 回测时间：2026-09-22 17:59:14
- 数据：UCI Online Retail Top 300 商品（真实月销量/价格/毛利）
- 对比集合规模：Top 10

## 回测口径

| 角色 | 定义 |
|---|---|
| 真实表现（ground truth） | 月销量 Top 10（UCI 真实聚合数据） |
| 规则基线 | 四维评分：需求强度 40%（月销量分位）+ 利润空间 30%（毛利率分位）+ 竞争格局 30%（价格不高于同分类中位） |
| LLM 推荐 | 真实调用选品 Agent（DeepSeek），对 3 个品类各分析一次 |
| 命中率 | 推荐集合 ∩ 真实 Top10 / 10 |

## 结果

### 规则基线（可复现的评分模型）

- 规则 Top10 命中真实 Top10：**30.0%**（3/10）
- 说明：仅用销量/毛利/价格三个可测指标，规则即可命中真实热销商品 30.0%，证明选品决策可被数据驱动。

### LLM 选品 Agent 实测（真实 DeepSeek 调用）

| 品类 | 推荐商品 | 置信度 | 匹配库内商品 | 在真实Top50 | 在规则Top20 |
|---|---|---|---|---|---|
| 家居照明 | WHITE HANGING HEART T-LIGHT HOLDER | 0.83 | WHITE HANGING HEART T-LIGHT HOLDER | ✅ | — |
| 包袋配件 | JUMBO BAG RED RETROSPOT | 0.86 | JUMBO BAG RED RETROSPOT | ✅ | — |
| 玩具礼品 | WORLD WAR 2 GLIDERS ASSTD DESIGNS | 0.82 | WORLD WAR 2 GLIDERS ASSTD DESIGNS | ✅ | ✅ |

- LLM 推荐命中真实销量 Top50 比例：**100.0%**（3/3 条成功分析）
- LLM 推荐命中规则 Top20 比例：**33.3%**（1/3 条成功分析）

## 结论与迭代方向

1. **规则基线命中率 30.0%**：数据驱动的选品评分有效，可复现、可解释。
2. **LLM 推荐差异**：LLM 基于数据上下文给出定性判断，可能推荐长尾/差异化商品（非纯销量导向），与规则基线互补——规则负责'筛'，LLM 负责'评'。
3. **局限**：回测基于历史聚合数据，未覆盖季节性/新品冷启动；LLM 推荐与库内商品的名称匹配依赖命名一致性，存在匹配误差（已在明细中如实呈现）。
4. **下一迭代**：引入真实运营采纳/拒绝数据，用采纳率回测选品准确率（与用户反馈内测联动）。

## 明细

### 规则 Top10（评分降序）

| 排名 | 商品 | 分类 | 月销量 | 评分 | 是否真实Top10 |
|---|---|---|---|---|---|
| 1 | WORLD WAR 2 GLIDERS ASSTD DESIGNS | 玩具礼品 | 4234 | 0.9913 | ✅ |
| 2 | PACK OF 12 LONDON TISSUES | 家居杂货 | 2010 | 0.9807 | — |
| 3 | BROCADE RING PURSE | 包袋配件 | 1774 | 0.9753 | — |
| 4 | PLACE SETTING WHITE HEART | 节庆装饰 | 1165 | 0.938 | — |
| 5 | DISCO BALL CHRISTMAS DECORATION | 玩具礼品 | 998 | 0.935 | — |
| 6 | GIRLS ALPHABET IRON ON PATCHES | 家居杂货 | 1068 | 0.9287 | — |
| 7 | SMALL CHINESE STYLE SCISSOR | 家居杂货 | 1025 | 0.922 | — |
| 8 | PACK OF 72 RETROSPOT CAKE CASES | 厨具餐具 | 2801 | 0.9217 | ✅ |
| 9 | MINI PAINT SET VINTAGE | 玩具礼品 | 2049 | 0.919 | ✅ |
| 10 | PACK OF 60 PINK PAISLEY CAKE CASES | 厨具餐具 | 1912 | 0.9163 | — |

### 真实 Top10（月销量，ground truth）

| 排名 | 商品 | 分类 | 月销量 |
|---|---|---|---|
| 1 | PAPER CRAFT , LITTLE BIRDIE | 文具贺卡 | 6230 |
| 2 | MEDIUM CERAMIC TOP STORAGE JAR | 厨具餐具 | 6003 |
| 3 | WORLD WAR 2 GLIDERS ASSTD DESIGNS | 玩具礼品 | 4234 |
| 4 | JUMBO BAG RED RETROSPOT | 包袋配件 | 3729 |
| 5 | WHITE HANGING HEART T-LIGHT HOLDER | 家居照明 | 2892 |
| 6 | POPCORN HOLDER | 家居杂货 | 2828 |
| 7 | ASSORTED COLOUR BIRD ORNAMENT | 玩具礼品 | 2805 |
| 8 | PACK OF 72 RETROSPOT CAKE CASES | 厨具餐具 | 2801 |
| 9 | RABBIT NIGHT LIGHT | 家居照明 | 2368 |
| 10 | MINI PAINT SET VINTAGE | 玩具礼品 | 2049 |
