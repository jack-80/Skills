#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the canonical analysis JSON before building the report.

Catches the mistakes that silently turn into "—" in the report: missing keys,
percentages written as 0-1 fractions, star distributions that do not sum to 100,
numbers that disagree between sections, and cost breakdowns that do not add up.

Usage:
    python3 validate_data.py data.json
    python3 validate_data.py data.json --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

PERCENT_HINT = ("naturalShare", "adShare", "adSalesShare", "conversion", "acos", "tacos",
                "grossMargin", "netMargin")


def num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "").replace("%", ""))
        except ValueError:
            return None
    return None


class Checker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def note(self, message):
        self.notes.append(message)


def get(data, *path):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def check_identity(data, checker):
    asin = get(data, "meta", "asin")
    if not asin:
        checker.error("meta.asin 缺失：报告无法定位商品，build_report.py 会直接退出。")
    elif not re.fullmatch(r"[A-Z0-9]{10}", str(asin).strip().upper()):
        checker.warn(f"meta.asin 取值 {asin!r} 不像标准 ASIN（应为 10 位大写字母数字）。")
    if not get(data, "meta", "marketplace"):
        checker.note("meta.marketplace 未填，报告按 US 站点假设处理，请在报告中写明这一假设。")
    if not get(data, "meta", "dataWindow"):
        checker.warn("meta.dataWindow 未填：没有数据窗口，读者无法判断数据的时效性。")


def check_summary(data, checker):
    summary = data.get("summary") or {}
    if not summary:
        checker.error("summary 缺失：报告将没有「总结」要素（执行摘要为空）。")
        return
    if not summary.get("headline"):
        checker.error("summary.headline 缺失：缺少一句话结论，「总结」要素不完整。")
    if not summary.get("insights"):
        checker.warn("summary.insights 为空：建议补 3–5 条关键洞察。")
    actions = summary.get("actions") or []
    if not actions:
        checker.warn("summary.actions 为空：运营报告需要可执行的行动建议。")
    else:
        for index, action in enumerate(actions, 1):
            if not action.get("priority"):
                checker.warn(f"summary.actions[{index}] 缺少 priority（P0/P1/P2）。")
            if not action.get("expectedImpact"):
                checker.warn(f"summary.actions[{index}] 缺少 expectedImpact（预期影响）。")
    if not summary.get("risks"):
        checker.note("summary.risks 为空：建议至少写一条风险（库存、评分、广告依赖等）。")


def check_comparisons(data, checker):
    has_competitors = bool([c for c in (data.get("competitors") or []) if c])
    has_benchmark = bool([r for r in get(data, "benchmark", "rows") or [] if r])
    has_trend = bool([r for r in get(data, "trendCompare", "rows") or [] if r])
    if not has_competitors:
        checker.error("competitors 为空：缺少横向对比，「数据对比」要素不完整。")
    elif len(data["competitors"]) < 3:
        checker.warn(f"competitors 只有 {len(data['competitors'])} 个，建议 4–6 个可比竞品。")
    if not has_benchmark:
        checker.warn("benchmark 为空：没有品类基准，对比缺少参照系。")
    if not has_trend:
        checker.warn("trendCompare 为空：缺少纵向（本期 vs 上期）对比。"
                     "若确实拿不到时间序列，请在 gaps 里写明缺什么数据。")
    for index, row in enumerate(data.get("competitors") or [], 1):
        missing = [key for key in ("price", "rating", "reviewCount", "bsr") if num(row.get(key)) is None]
        if missing:
            checker.warn(f"competitors[{index}]（{row.get('asin', '未命名')}）缺字段："
                         f"{', '.join(missing)}——对比表该列会显示为「—」。")


def check_percentages(data, checker):
    suspicious = []
    for key in PERCENT_HINT:
        value = num(get(data, "traffic", key))
        if value is None:
            value = num(get(data, "economics", key))
        if value is not None and 0 < value <= 1:
            suspicious.append(key)
    distribution = get(data, "reviews", "starDistribution") or {}
    values = [num(v) for v in distribution.values() if num(v) is not None]
    if values and max(values) <= 1:
        suspicious.append("reviews.starDistribution")
    if suspicious:
        checker.warn("以下字段取值都 ≤ 1，疑似用了 0–1 小数；本技能的约定是百分比填 0–100："
                     + ", ".join(suspicious))

    if values:
        total = sum(values)
        if abs(total - 100) > 2:
            checker.warn(f"reviews.starDistribution 合计 {total:g}%，不等于 100%，"
                         "请确认是否漏了某一档或用了数量而非百分比。")

    natural, ad = num(get(data, "traffic", "naturalShare")), num(get(data, "traffic", "adShare"))
    if natural is not None and ad is not None and abs(natural + ad - 100) > 1:
        checker.warn(f"traffic.naturalShare({natural:g}%) + adShare({ad:g}%) = "
                     f"{natural + ad:g}%，两者应合计 100%。")


def check_consistency(data, checker):
    pairs = [
        (("snapshot", "price"), ("price", "current"), "价格"),
        (("snapshot", "rating"), ("reviews", "rating"), "平均星级"),
        (("snapshot", "reviewCount"), ("reviews", "count"), "评论总数"),
        (("snapshot", "bsr"), ("rank", "current"), "BSR"),
    ]
    for first, second, label in pairs:
        left, right = num(get(data, *first)), num(get(data, *second))
        if left is None or right is None:
            continue
        if abs(left - right) > max(abs(right) * 0.02, 0.05):
            checker.warn(f"{label}在两个位置不一致：{'.'.join(first)}={left:g}，"
                         f"{'.'.join(second)}={right:g}——报告里会出现对不上的两处数字。")

    price = num(get(data, "economics", "price"))
    profit = num(get(data, "economics", "grossProfit"))
    costs = [num(get(data, "economics", key)) for key in
             ("referralFee", "fbaFee", "cogs", "firstLeg", "adCostPerUnit", "storage", "other")]
    costs = [c for c in costs if c is not None]
    if price is not None and profit is not None and len(costs) >= 3:
        computed = price - sum(costs)
        if abs(computed - profit) > 0.1:
            checker.warn(f"利润拆解对不上：售价 {price:g} − 各项成本 {sum(costs):.2f} = "
                         f"{computed:.2f}，但 grossProfit 填的是 {profit:g}。")

    units = num(get(data, "inventory", "availableUnits"))
    daily = num(get(data, "inventory", "dailySales"))
    cover = num(get(data, "inventory", "daysOfCover"))
    if units is not None and daily and cover is not None:
        computed = units / daily
        if abs(computed - cover) > max(computed * 0.2, 1):
            checker.warn(f"可售天数对不上：可售 {units:g} / 日均 {daily:g} = {computed:.1f} 天，"
                         f"但 daysOfCover 填的是 {cover:g}。")


def check_sources(data, checker):
    sources = [s for s in (data.get("sources") or []) if s]
    if not sources:
        checker.error("sources 为空：每个数字都必须能追到来源，否则无法判断可信度。")
        return
    for index, source in enumerate(sources, 1):
        if not source.get("confidence"):
            checker.warn(f"sources[{index}]（{source.get('name', '未命名')}）缺少 confidence（高/中/低）。")
        if not source.get("type"):
            checker.warn(f"sources[{index}] 缺少 type（export/api/browser/manual）。")
    if not [g for g in (data.get("gaps") or []) if g]:
        low_conf = [s for s in sources if str(s.get("confidence")) in ("低", "low")]
        if low_conf:
            checker.warn(f"有 {len(low_conf)} 个低置信度来源，但 gaps 为空："
                         "请把由此产生的不确定性写进 gaps。")


def estimate_report(data):
    """Mirror the section/chart logic in build_report.py so the agent knows what will render."""
    sections, charts = [], 0
    if data.get("summary"):
        sections.append("执行摘要")
    if data.get("snapshot"):
        sections.append("产品概览")
    if data.get("price"):
        sections.append("价格与促销")
        charts += 1 if len(get(data, "price", "series") or []) >= 2 else 0
    if data.get("rank") or data.get("sales"):
        sections.append("排名与销量")
        charts += 1 if len(get(data, "rank", "series") or []) >= 2 else 0
        monthly = get(data, "sales", "monthly") or []
        if monthly:
            charts += 1
            if any(num(m.get("revenue")) is not None for m in monthly):
                charts += 1
    if data.get("reviews"):
        sections.append("评论与口碑")
        if get(data, "reviews", "starDistribution"):
            charts += 1
        history = get(data, "reviews", "history") or []
        if len(history) >= 2:
            charts += 1
            if any(num(h.get("rating")) is not None for h in history):
                charts += 1
    if data.get("traffic"):
        sections.append("流量与关键词")
        if num(get(data, "traffic", "naturalShare")) is not None:
            charts += 1
        if get(data, "traffic", "keywords"):
            charts += 1
    if [c for c in (data.get("competitors") or []) if c]:
        sections.append("竞品对比（横向）")
        charts += 4
        if len(data["competitors"]) >= 2:
            charts += 1
    if [r for r in get(data, "benchmark", "rows") or [] if r]:
        sections.append("品类基准达标")
        charts += 1
    if [r for r in get(data, "trendCompare", "rows") or [] if r]:
        sections.append("纵向对比（本期 vs 上期）")
        charts += 1
    if data.get("economics"):
        sections.append("利润与成本")
        cost_items = [k for k in ("referralFee", "fbaFee", "cogs", "firstLeg",
                                  "adCostPerUnit", "storage", "other")
                      if num(get(data, "economics", k)) is not None]
        charts += 1 if len(cost_items) >= 2 else 0
    if data.get("inventory"):
        sections.append("库存与补货风险")
    if data.get("sources") or data.get("gaps"):
        sections.append("数据质量与缺口")
    if data.get("methods"):
        sections.append("方法与假设")
    return sections, charts


def main():
    parser = argparse.ArgumentParser(description="Validate the canonical Amazon analysis JSON.")
    parser.add_argument("data", help="path to the canonical analysis JSON")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args()

    path = os.path.expanduser(args.data)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print(f"[ERROR] 找不到文件：{path}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"[ERROR] JSON 解析失败：第 {exc.lineno} 行第 {exc.colno} 列 —— {exc.msg}")
        print("        常见原因：多/少一个逗号、中文引号“”、尾随逗号。")
        return 1

    checker = Checker()
    check_identity(data, checker)
    check_summary(data, checker)
    check_comparisons(data, checker)
    check_percentages(data, checker)
    check_consistency(data, checker)
    check_sources(data, checker)
    sections, charts = estimate_report(data)

    if args.json:
        print(json.dumps({
            "ok": not checker.errors,
            "errors": checker.errors,
            "warnings": checker.warnings,
            "notes": checker.notes,
            "sections": sections,
            "estimated_charts": charts,
        }, ensure_ascii=False, indent=2))
        return 1 if checker.errors else 0

    print(f"校验文件：{os.path.abspath(path)}")
    print(f"预计渲染：{len(sections)} 个章节 / 约 {charts} 张图表")
    print(f"          {' / '.join(sections) if sections else '（无）'}")
    print()
    for message in checker.errors:
        print(f"[ERROR] {message}")
    for message in checker.warnings:
        print(f"[WARN]  {message}")
    for message in checker.notes:
        print(f"[INFO]  {message}")

    if checker.errors:
        print(f"\n结果：{len(checker.errors)} 个错误、{len(checker.warnings)} 个警告 —— 先修错误再生成报告。")
        return 1
    print(f"\n结果：通过（{len(checker.warnings)} 个警告，确认后可继续生成报告）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
