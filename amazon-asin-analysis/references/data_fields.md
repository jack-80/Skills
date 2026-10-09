# 字段清单、数据格式与估算口径

分析数据统一写入 `amazon_<ASIN>_data.json`。**所有字段可缺省**：缺失的键直接不写，
`build_report.py` 会跳过对应图表；被判定为必要的缺口由 `validate_data.py` 报出来，逐条写进 `gaps`。

## 一、数据格式（canonical JSON）

```json
{
  "meta": {
    "asin": "B0XXXXXXXX", "marketplace": "US",
    "title": "", "brand": "", "category": "", "subCategory": "",
    "currency": "USD",
    "dataWindow": "2026-06-01 ~ 2026-08-31",
    "snapshotTime": "2026-09-13"
  },
  "summary": {
    "headline": "一句话结论",
    "keyNumbers": [
      { "label": "价格 vs 品类基准", "value": "-18.4%", "delta": -18.4, "better": "higher", "hint": "目标 $19.99 / 基准 $24.50" }
    ],
    "insights": ["3–5 条最高价值结论"],
    "actions": [
      { "priority": "P0", "action": "做什么", "rationale": "依据", "expectedImpact": "预期影响" }
    ],
    "risks": ["风险项"]
  },
  "snapshot": {
    "price": 19.99, "listPrice": 24.99, "rating": 4.2, "reviewCount": 1234,
    "bsr": 1340, "bsrCategory": "Home & Kitchen", "subCategoryRank": 42,
    "variants": 6, "fulfillment": "FBA", "coupon": "5% Coupon",
    "qa": 42, "firstAvailable": "2024-03-01", "images": 7,
    "hasAplus": true, "hasVideo": false, "bulletCount": 5, "seller": "",
    "variantPriceMin": 17.99, "variantPriceMax": 24.99,
    "returnBadge": "亚马逊在商品页展示「经常退货」（Frequently returned item）标记"
  },
  "price": {
    "current": 19.99, "listPrice": 24.99, "avg30": 19.60, "min": 17.99, "max": 24.99,
    "series": [{ "date": "2026-08-01", "price": 19.99 }],
    "promotions": [{ "period": "2026-07-15 ~ 07-18", "type": "Coupon 10%", "priceEffect": "到手 $18.99" }]
  },
  "rank": {
    "current": 1340, "best": 1200, "worst": 1980, "category": "Home & Kitchen",
    "series": [{ "date": "2026-08-01", "rank": 1340 }]
  },
  "sales": {
    "monthly": [{ "month": "2026-06", "units": 700, "revenue": 13993 }],
    "method": "BSR 反推", "confidence": "低"
  },
  "reviews": {
    "rating": 4.2, "count": 1234, "newLast30d": 38, "ratingLast30d": 3.9,
    "starDistribution": { "5": 55, "4": 18, "3": 9, "2": 6, "1": 12 },
    "history": [{ "date": "2026-08-01", "count": 1200, "rating": 4.2 }],
    "positiveThemes": [{ "theme": "音质清晰", "pct": 32 }],
    "negativeThemes": [{ "theme": "连接不稳定", "pct": 24 }],
    "trend": "评分走势判断", "sampleSize": 100
  },
  "traffic": {
    "sessions": 8600, "conversion": 11.2, "naturalShare": 62, "adShare": 38,
    "acos": 31, "tacos": 9, "adSalesShare": 29,
    "keywords": [
      { "keyword": "wireless earbuds", "searchVolume": 40500, "ourRank": 12,
        "trafficShare": 11, "clickShare": 6, "conversionShare": 4 }
    ]
  },
  "economics": {
    "price": 19.99,
    "referralFee": 3.00, "fbaFee": 4.15, "cogs": 5.20, "firstLeg": 0.80,
    "adCostPerUnit": 1.35, "storage": 0.15, "other": 0.00,
    "grossProfit": 5.49, "grossMargin": 27.5, "netMargin": 21.0
  },
  "inventory": {
    "availableUnits": 560, "dailySales": 26.7, "daysOfCover": 21,
    "inboundUnits": 0, "daysToRestock": 35, "risk": "高"
  },
  "competitors": [
    { "asin": "B0AAAAAAAA", "title": "", "brand": "BrandX", "price": 24.99, "rating": 4.6,
      "reviewCount": 3010, "bsr": 980, "monthlyUnits": 1500, "variants": 4,
      "fulfillment": "FBA", "note": "" }
  ],
  "benchmark": {
    "label": "类目 Top20 中位数",
    "rows": [
      { "metric": "价格", "subject": 19.99, "benchmark": 24.50, "unit": "USD", "better": "neutral" },
      { "metric": "平均星级", "subject": 4.20, "benchmark": 4.45, "unit": "星", "better": "higher", "tolerance": 0.1 }
    ]
  },
  "trendCompare": {
    "currentLabel": "本期 2026-07~08", "previousLabel": "上期 2026-05~06",
    "rows": [{ "metric": "月均销量", "current": 800, "previous": 700, "unit": "件", "better": "higher" }]
  },
  "sources": [
    { "name": "Amazon 商品页", "type": "browser", "url": "https://www.amazon.com/dp/B0XXXXXXXX",
      "retrievedAt": "2026-09-13 10:20", "coverage": "价格/评分/评论数/BSR", "confidence": "中" }
  ],
  "gaps": ["无广告报表，无法判断增长来自自然流量还是广告投放"],
  "methods": ["月销量由 BSR 反推，误差 ±30%"]
}
```

### 两条容易踩的格式约定

- **百分比一律填 0–100 的数值**（`11.2` 表示 11.2%，`starDistribution` 的 `"5": 55` 表示 55%）。
  不要填 `0.112`。`validate_data.py` 会检测"全部小于等于 1"的可疑写法并提醒。
- **BSR 是数值越小越好**；在 `benchmark` / `trendCompare` 的 `better` 字段里填 `"lower"`，
  报告会据此判断达标与涨跌方向的好坏。
- `benchmark.rows[].better` 还支持 `"neutral"`：该指标只做定位参考、不判定达标（价格通常属于这一类，
  便宜既是引流优势也是毛利损失，方向好坏取决于阶段目标）。
- `benchmark.rows[].tolerance` 可选，填绝对值容差：`|本 ASIN − 基准| ≤ tolerance` 判为持平。
  星级这类小数度量用它更准（如 `0.1`），不填则按 ±10% 的相对口径判定。
- `snapshot.returnBadge` 填亚马逊的退货标记（有就填字符串或 `true`，没有就省略）。报告会在页头和「产品概览」
  双重高亮，图表之外单独提示——这是转化与退货风险的一手信号。
- `snapshot.variantPriceMin` / `variantPriceMax`：同一父体下变体的售价区间，用于说明变体之间存在的价差。
- `competitors[].brand` **必须尽力填**：报告在对比表列头、柱状图横轴、散点图与 CSV 中都用「品牌 + ASIN」标识竞品。
  页面确实未标注品牌时留空，报告会自动降级为只显示 ASIN，并在图表注释里说明——不要猜品牌。

## 二、采集字段与来源映射

### 基础信息

| 字段 | 首选来源 | 降级来源 |
|------|----------|----------|
| ASIN / 站点 tld | 用户输入 | URL 解析，默认 `com` |
| 标题 / 品牌 / 型号 | 商品页 | 搜索结果 / 用户导出 |
| 类目面包屑、子类目排名 | 商品页 | 类目 Best Sellers |
| 首次上架日期、变体数 | 商品页 | 连接器 |
| 主图数量 / A+ / 视频 / 五点条数 | 商品页 | — |

### 价格与排名

| 字段 | 首选来源 | 降级来源 |
|------|----------|----------|
| 标价、Buy Box 价、币种 | 商品页 / 连接器 | 第三方聚合快照 |
| 价格历史（日/周粒度） | Keepa / 卖家精灵导出 | — |
| BSR、BSR 子类目 | 商品页 | 连接器 |
| BSR 历史曲线 | 连接器 / 导出 | — |
| 优惠券 / 秒杀 / 会员折扣 | 商品页 | 广告报表 |
| FBA / 自发货 | 商品页 | — |

### 评论与评分

| 字段 | 首选来源 | 降级来源 |
|------|----------|----------|
| 平均星级、评论总数 | 商品页 / 连接器 | 搜索结果 |
| 评分分布 5★~1★ | 商品页 | 由近期评论样本归并估算（须标"基于样本估算"） |
| 评论增长曲线 | 连接器 / 定期快照 | — |
| 近 30 天新增评论数、近 30 天均分 | 评论页按日期统计 | 样本估算 |
| 正/负向主题与提及占比 | 最新 50–100 条评论文本 | 商品页"热门评论"摘要 |

### 运营指标（本技能的运营分析核心）

| 字段 | 来源 | 说明 |
|------|------|------|
| 销量与 GMV | Seller Central 业务报告 → 无则用 BSR 反推 | 反推必须标估算 |
| 会话数、转化率、退货率 | 业务报告（按 ASIN 明细） | 转化率 = 订单数 / 会话数 |
| 出单关键词、点击/转化份额 | 品牌分析 SQP | 需品牌备案 |
| 自然 / 广告流量占比 | SQP + 广告报表 | 口径写进 methods |
| ACOS、TACOS、广告销售占比 | 广告报表 | TACOS = 广告花费 / 总销售额 |
| 佣金、FBA 配送费、仓储费 | 亚马逊费用预览 / 收入计算器 | 按站点费率表 |
| 采购成本、头程、单件广告成本 | 用户提供 / 广告报表 | 拿不到就留空，不要套用"行业平均" |
| 库存可售天数、在途、补货周期 | 库存报表 / FBA 后台 | 可售天数 = 可售库存 / 日均销量 |
| 退货标记（Frequently returned item） | 商品页 | 亚马逊只在退货率显著高于同类时展示；无具体退货率可读 |
| 变体价带 | 商品页变体区 | 同一父体不同颜色/尺寸的售价区间 |

## 三、估算口径（必须写进 `methods`）

只在拿不到真实数据时使用，且必须在报告里显式标注方法与误差。

| 指标 | 方法 | 必须标注 |
|------|------|----------|
| 月销量 | 同子类目 BSR 分段映射（先用同品类真实销量做锚点校准，锚点越近越准） | "BSR 反推，误差 ±30%" |
| 月 GMV | 月销量 × 期末售价 | 与销量同样置信度 |
| 评分分布 | 近期评论样本按星级归并 | "基于 N 条评论样本估算" |
| 评论增速 | 两个时间点的评论数差 / 间隔天数 | 标出两个时间点 |
| 利润 | 售价 − 佣金 − FBA − 采购 − 头程 − 广告 − 仓储 − 其它 | 未拿到的成本项写明"未计入" |
| 品类基准 | 可比竞品的中位数（不用均值，避免极端值带偏） | "基于 N 个可比竞品的中位值" |

**禁止**：用"行业平均毛利率""一般转化率"之类外部常识去填用户的实际经营指标。
这类数字一旦进报告就会被当成该 ASIN 的真实数据使用。

## 四、采集执行提示

1. 价格、BSR、评论数波动大——每个快照都记时间戳，报告里标"快照时间"。
2. 同一字段有多个来源时，取权威性最高的，并在 `sources.coverage` 里说明。
3. 每个数值在内部记录来源与置信度，便于报告脚注引用。
4. 填完 JSON 先跑 `validate_data.py`，不要凭感觉认为填全了。
