---
name: amazon-asin-analysis
description: "对一个 Amazon ASIN 做全维度运营数据分析，产出含执行总结、内联 SVG 图表与横向/纵向数据对比的自包含 HTML 报告。当用户只给一个 ASIN（如 B0XXXXXXXX）或 Amazon 商品链接，要求做产品分析、竞品对标、价格/评论/排名/销量/利润/库存诊断或运营分析报告时使用。"
metadata:
  short-description: "输入一个 ASIN，产出含总结、图表、对比的运营分析报告"
  version: "1.1.0"
---

# Amazon ASIN 全维度运营分析

用户可能只给一个 ASIN，其余什么都不给——这是本技能的默认触发场景，也是必须能跑通的场景。

## 交付物（三要素缺一不可）

1. **总结** —— 执行摘要：一句话结论 + 关键数字 + 洞察 + 分级行动建议 + 风险。
2. **图表** —— 至少 4 张，全部内联 SVG，离线和无网络都能打开。
3. **数据对比** —— 横向（vs 竞品 vs 品类基准）+ 纵向（本期 vs 上期）双向对比。

产出物：

- `<workdir>/amazon_<ASIN>_report.html` —— 自包含单文件报告（主交付物）
- `<workdir>/amazon_<ASIN>_data.json` —— 规范化数据（可复现、可复核）
- `<workdir>/csv/amazon_<ASIN>_*.csv` —— 对比表与原始序列（可选，用户要自己再算时给）
- 对话内 Markdown 简报 —— 摘要 + 对比表，便于即时阅读

## 数据诚信（硬规则）

- **禁止编造**。任何百分比、销量、排名、费用都不得凭空生成。拿不到的字段写进 `gaps`，在报告「数据质量」章节列明，不得用"约"字掩盖猜测。
- 每个数据源登记 `sources`，含 `type`（export/api/browser/manual）、取数时间、覆盖字段、置信度（高/中/低）。
- 估算值必须写明方法（如"由 BSR 反推，误差 ±30%"），并标 `confidence: "低"`。
- 引用工具名称、字段名、URL 一律用实际取得的，不虚构接口和文档链接。
- **价格必须写清口径**：站点 + 配送地 + 币种。做美国市场分析就用美国本土口径（amazon.com + 美国 ZIP + 英文界面），
  并把配送地写进 `sources`。跨境显示价（本币折算 + 进口费）不得用于定价结论。
- **对比必须同形态**：多件套只和多件套比、直排只和直排比。头部产品的量级差距放正文当参照，不塞进中位数基准。
- **竞品必须带品牌**：每个竞品填 `brand`（页面没标就留空，不猜），报告会自动用「品牌 + ASIN」标识。
- 页面上出现买家的退货标记（Frequently returned item / 经常退货）时，必须写入 `snapshot.returnBadge` 并高亮。

## 工作流

### 1. 归一化输入

- ASIN：10 位大写字母数字。用户给 URL 时从 `/dp/<ASIN>` 或 `/gp/product/<ASIN>` 提取。
- 站点：从 URL 域名或用户语言推断，默认 `amazon.com`（US）。**在报告中显式写明站点假设**。
- 建 `<workdir>/amazon_<ASIN>_data.json`，按 `references/data_fields.md` 的字段表逐步填充。

### 2. 取数（按阶梯降级）

严格按 `references/data_acquisition.md` 的顺序尝试，**先本地、后网络**：

1. **本地已有导出文件**——工作区/用户目录里的 Keepa CSV、卖家精灵/Helium 10 导出、Seller Central 业务报告与搜索词报告、广告报表。这是离线环境下唯一的高精度来源，优先全盘扫描。
2. **已连接的连接器或 API**——环境里实际存在且已授权的电商数据 MCP / API。
3. **公开页面**——用环境实际具备的浏览器能力读取商品页、评论页；需要用户授权时先请求授权。Amazon 反爬强，评论页常需登录，失败即降级，不要反复重试。
4. **请用户补数据**——前三步都拿不到时，输出明确的"待补数据清单"（要哪个文件、从 Seller Central 哪个菜单导出），并**照常出报告**：框架完整、已得字段照常展示、缺失字段标"待采集"。

任何一步拿到数据就登记来源与置信度，不要跳过登记。

> **用第 3 级（浏览器公开页面）之前，先确认"口径三件套"：站点、配送地、语言。**
> 目标市场是哪里，就用哪里的配送地址和语言——美国站必须把 Deliver to 设成美国 ZIP、界面切英文。
> 跨境口径（配送到境外 + 中文界面）会同时污染两件事：价格变成本币折算价、标题被翻译掩盖堆词问题。
> 操作细节与踩坑记录见 `references/data_acquisition.md` 的「口径硬要求」。

### 3. 补齐分析与对比

- 竞品与品类基准：读 `references/competitor_method.md`。
- 销量/广告/利润/库存等运营指标的口径与估算方法：读 `references/data_fields.md`。
- 纵向对比：从价格/BSR/评论/销量序列里切出"本期 vs 上期"两段，写入 `trendCompare`。

### 4. 生成与校验

```bash
python3 scripts/validate_data.py <workdir>/amazon_<ASIN>_data.json
python3 scripts/build_report.py --data <workdir>/amazon_<ASIN>_data.json \
    --out <workdir>/amazon_<ASIN>_report.html \
    --csv <workdir>/csv
```

- 先跑 `validate_data.py`，把报出的缺口补进 `gaps` 或补齐数据，再生成。
- `build_report.py` 只用 Python 标准库，不装依赖、不联网、不引用 CDN。
- `--csv` 可选：写出竞品对比、品类基准、纵向对比、关键词、利润拆解与原始序列的 CSV（UTF-8 BOM，Excel 直接打开不乱码）。
- 生成后按 `references/report_structure.md` 的清单自检，再用环境里的预览工具打开 HTML（Codex：`open_in_codex`）。

### 5. 交付

给出 HTML 的绝对路径 + 对话内 Markdown 简报（摘要 + 对比表）。简报与 HTML 内容一致、详略不同。

## 报告章节与图表

章节顺序、图表清单、写作口径见 `references/report_structure.md`。要点：

- 每张图配一句解读，不放"裸图"。
- BSR 越小越好、评论数是对数轴、价格带要标明币种——这类容易误读的地方必须标注。
- 图表由 `build_report.py` 从数据 JSON 直接生成，**不要手写 HTML 模板再填数**。
- 竞品对比统一用「品牌 + ASIN」标识；某指标只有本 ASIN 有值时不画对比图，改为在图注说明并写进 `gaps`。
- 退货标记（`snapshot.returnBadge`）会在页头与产品概览双重高亮，不要只写在正文里。

## 常见错误（都踩过，逐条避开）

1. **口径不一致**——目标和竞品不在同一站点/配送地/语言下取数，价格与币种不可比；或只改 URL 参数
   （`?language=en_US&currency=USD`）就以为切好了，实际被跨境 cookie 覆盖。取完数回读一次「Deliver to」确认。
2. **形态混比**——把单片式头部拉进多件套对比组算中位数，价格和评论资产会同时失真（实测把 1.3 倍算成了 5.8 倍）。
3. **把支付促销当折扣**——「Get $50 off instantly … Amazon Visa」是开卡权益，不是 Coupon 或划线价。
4. **只有本 ASIN 一根柱子的"对比图"**——竞品缺数据时应跳过该图并在图注说明，不要画出来充数。
5. **用估算值掩盖猜测**——"约"、"大概"不是标注，必须写明方法与误差，并标 `confidence: "低"`。

## 参考文件

- `references/data_acquisition.md` → 取数阶梯、本地文件解析、降级与合规。
- `references/data_fields.md` → 采集字段清单、来源映射、估算口径。
- `references/competitor_method.md` → 竞品筛选、品类基准、对比表与解读口径。
- `references/report_structure.md` → 章节结构、图表清单、写作口径、自检清单。

## 语言

报告正文用简体中文；ASIN、BSR、Buy Box、FBA、ACOS、TACOS 等术语保留英文。用户用其它语言提问时，把文案字段同步译成该语言，结构与口径不变。
