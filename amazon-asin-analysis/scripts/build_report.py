#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a self-contained Amazon ASIN analysis report (HTML + inline SVG charts).

Standard library only: no third-party package, no network, no CDN.
Charts are inline SVG that inherits CSS variables, so the report adapts to the
viewer's light/dark theme and renders identically offline.

Usage:
    python3 build_report.py --data data.json --out report.html
    python3 build_report.py --data data.json --out report.html --open
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys
import webbrowser

SVG_W = 760
CHART_COLORS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)", "var(--s6)"]
CUR_SYMBOL = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "RMB": "¥",
    "CAD": "C$", "AUD": "A$", "INR": "₹", "MXN": "MX$", "BRL": "R$", "SEK": "kr",
}


# ---------------------------------------------------------------- text helpers

def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def fmt(value, digits=None, money=False, currency="USD") -> str:
    f = num(value)
    if f is None:
        return "—"
    if digits is None:
        a = abs(f)
        digits = 0 if a >= 100 else (1 if a >= 10 else 2)
    body = f"{f:,.{digits}f}"
    if money:
        return CUR_SYMBOL.get((currency or "USD").upper(), "") + body
    return body


def fmt_int(value) -> str:
    f = num(value)
    return "—" if f is None else f"{f:,.0f}"


def fmt_pct(value, digits=1) -> str:
    f = num(value)
    return "—" if f is None else f"{f:,.{digits}f}%"


def axis_label(value) -> str:
    f = num(value)
    if f is None:
        return ""
    a = abs(f)
    if a >= 1e9:
        return f"{f / 1e9:.1f}B"
    if a >= 1e6:
        return f"{f / 1e6:.1f}M"
    if a >= 1e4:
        return f"{f / 1e3:.0f}K"
    if a >= 1e3:
        return f"{f / 1e3:.1f}K"
    if a >= 10:
        return f"{f:.0f}"
    if a >= 1:
        return f"{f:g}"
    return f"{f:.2f}".rstrip("0").rstrip(".")


def text_width(text, size=12) -> float:
    width = 0.0
    for ch in str(text):
        width += size * (1.0 if ord(ch) > 0x2E80 else 0.56)
    return width


def clip(text, limit=28) -> str:
    s = "" if text is None else str(text)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ---------------------------------------------------------------- chart scales

def linear_ticks(low, high, count=5):
    if not high > low:
        high = low + 1.0
    raw = (high - low) / max(count, 1)
    magnitude = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    step = magnitude
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * magnitude:
            step = mult * magnitude
            break
    start = math.floor(low / step) * step
    ticks, value, guard = [], start, 0
    while value <= high + step * 0.5 and guard < 200:
        ticks.append(round(value, 10))
        value += step
        guard += 1
    return ticks


def log_ticks(low, high):
    low = max(low, 1e-9)
    high = max(high, low * 10)
    ticks = []
    for exponent in range(math.floor(math.log10(low)), math.ceil(math.log10(high)) + 1):
        for mult in (1, 2, 5):
            tick = mult * 10 ** exponent
            if low * 0.85 <= tick <= high * 1.15:
                ticks.append(tick)
    return sorted(set(ticks)) or [low, high]


def make_scale(kind, low, high, top, bottom):
    if kind == "log":
        low = max(low, 1e-9)
        high = max(high, low * (1 + 1e-6))
        l0, l1 = math.log10(low), math.log10(high)

        def scale(value):
            value = max(value, low)
            return bottom - (math.log10(value) - l0) / (l1 - l0) * (bottom - top)

        return scale

    if not high > low:
        high = low + 1.0

    def scale(value):
        return bottom - (value - low) / (high - low) * (bottom - top)

    return scale


def make_scale_x(low, high, left, right):
    """Horizontal scale: low value at the left edge, high value at the right edge."""
    if not high > low:
        high = low + 1.0

    def scale(value):
        return left + (value - low) / (high - low) * (right - left)

    return scale


def spans_a_decade(values):
    positives = [v for v in values if v is not None and v > 0]
    if len(positives) < 2:
        return False
    return max(positives) / min(positives) >= 10


def svg_open(height):
    return (
        f'<svg class="chart" viewBox="0 0 {SVG_W} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" xmlns="http://www.w3.org/2000/svg">'
    )


def grid_and_axis(parts, ticks, scale, left, right):
    for tick in ticks:
        y = scale(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--muted)">{esc(axis_label(tick))}</text>'
        )


def bar_chart(categories, values, *, height=300, kind="linear", highlight=0, digits=None,
              money=False, currency="USD", suffix="", ref=None, ref_label=None, note="",
              colors=None, zero_base=True):
    """Vertical bar chart. Supports negative values and a log scale."""
    categories = list(categories)
    values = [num(v) for v in values]
    if not categories or not any(v is not None for v in values):
        return ""
    if money and digits is None:
        digits = 2
    requested_log = kind == "log"

    present = [v for v in values if v is not None]
    left, right, top = 74.0, SVG_W - 18.0, 28.0
    two_line = any("\n" in str(c) for c in categories)
    bottom = height - (76.0 if two_line else 56.0)
    plot_w = right - left

    if kind == "log" and spans_a_decade(present):
        low, high = min(present) * 0.6, max(present) * 1.8
        ticks = log_ticks(low, high)
    else:
        kind = "linear"
        if requested_log:
            note = (note + "　" if note else "") + "各值跨度不足一个数量级，已改用线性轴。"

    if kind == "linear":
        if zero_base:
            low = min(0.0, min(present) * 1.15)
            high = max(0.0, max(present) * 1.18)
        else:
            low = min(present) * 0.97
            high = max(present) * 1.03
        if high <= low:
            high = low + 1.0
        ticks = [t for t in linear_ticks(low, high, 5) if low - 1e-9 <= t <= high + 1e-9]

    scale = make_scale(kind, low, high, top, bottom)
    parts = [svg_open(height)]
    grid_and_axis(parts, ticks, scale, left, right)
    zero_y = scale(0.0) if low < 0 else scale(low)
    if low < 0:
        parts.append(
            f'<line x1="{left}" y1="{zero_y:.1f}" x2="{right}" y2="{zero_y:.1f}" '
            f'stroke="var(--axis)" stroke-width="1.2"/>'
        )

    slot = plot_w / len(categories)
    bar_w = min(slot * 0.62, 62)
    label_lines = [str(c).split("\n") for c in categories]
    rotate = max(max(text_width(p) for p in lines) for lines in label_lines) > slot - 8

    for index, (category, value) in enumerate(zip(categories, values)):
        center = left + slot * index + slot / 2
        if value is None:
            parts.append(
                f'<text x="{center:.1f}" y="{zero_y - 6:.1f}" text-anchor="middle" '
                f'font-size="11" fill="var(--muted)">—</text>'
            )
        else:
            y = scale(value)
            y0, y1 = min(y, zero_y), max(y, zero_y)
            if colors and index < len(colors):
                fill = colors[index]
            elif index == highlight:
                fill = "var(--accent)"
            else:
                fill = CHART_COLORS[1]
            parts.append(
                f'<rect x="{center - bar_w / 2:.1f}" y="{y0:.1f}" width="{bar_w:.1f}" '
                f'height="{max(y1 - y0, 1.2):.1f}" rx="3" fill="{fill}"/>'
            )
            text = fmt(value, digits, money=money, currency=currency) + suffix
            label_y = y0 - 6 if value >= 0 else y1 + 14
            parts.append(
                f'<text x="{center:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                f'font-size="11" fill="var(--text2)">{esc(text)}</text>'
            )
        if rotate:
            flat = " ".join(label_lines[index])
            anchor_y = bottom + 14
            parts.append(
                f'<text x="{center:.1f}" y="{anchor_y:.1f}" text-anchor="end" font-size="11" '
                f'fill="var(--muted)" transform="rotate(-35 {center:.1f} {anchor_y:.1f})">'
                f"{esc(clip(flat, 22))}</text>"
            )
        else:
            for line_index, line in enumerate(label_lines[index]):
                size = 11 if line_index == 0 else 10
                color = "var(--text2)" if line_index == 0 else "var(--muted)"
                parts.append(
                    f'<text x="{center:.1f}" y="{bottom + 16 + 14 * line_index:.1f}" '
                    f'text-anchor="middle" font-size="{size}" fill="{color}">'
                    f"{esc(clip(line, 20))}</text>"
                )

    if ref is not None and kind == "linear" and low <= ref <= high:
        y = scale(ref)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="var(--warn)" '
            f'stroke-width="1.6" stroke-dasharray="6 4"/>'
        )
        label = f"{ref_label or '基准'} {fmt(ref, digits, money=money, currency=currency)}"
        parts.append(
            f'<text x="{right - 4}" y="{y - 6:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--warn)">{esc(label)}</text>'
        )

    parts.append("</svg>")
    tail = f'<div class="chart-note">{esc(note)}</div>' if note else ""
    return "".join(parts) + tail


def hbar_chart(labels, values, *, height=None, digits=None, highlight=0, colors=None,
               money=False, currency="USD", suffix="", note="", label_width=176):
    """Horizontal bar chart, used for keywords and the cost breakdown."""
    rows = [(label, num(value)) for label, value in zip(labels, values)]
    rows = [row for row in rows if row[1] is not None]
    if not rows:
        return ""
    if money and digits is None:
        digits = 2

    row_h = 30.0
    top = 14.0
    height = height or int(top * 2 + row_h * len(rows))
    left = float(label_width) + 12
    right = SVG_W - 84.0
    plot_w = max(right - left, 40.0)
    high = max(value for _, value in rows) or 1.0

    parts = [svg_open(height)]
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + row_h * len(rows):.1f}" '
        f'stroke="var(--axis)" stroke-width="1"/>'
    )
    for index, (label, value) in enumerate(rows):
        center = top + row_h * index + row_h / 2
        width = max(plot_w * (value / (high * 1.12)), 1.5)
        fill = colors[index] if colors and index < len(colors) else (
            "var(--accent)" if index == highlight else CHART_COLORS[1]
        )
        parts.append(
            f'<rect x="{left}" y="{center - 7:.1f}" width="{width:.1f}" height="14" '
            f'rx="3" fill="{fill}" opacity="{1.0 if index == highlight else 0.88}"/>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{center + 4:.1f}" text-anchor="end" font-size="12" '
            f'fill="var(--text2)">{esc(clip(label, 22))}</text>'
        )
        text = fmt(value, digits, money=money, currency=currency) + suffix
        parts.append(
            f'<text x="{left + width + 8:.1f}" y="{center + 4:.1f}" font-size="11.5" '
            f'fill="var(--text2)">{esc(text)}</text>'
        )
    parts.append("</svg>")
    tail = f'<div class="chart-note">{esc(note)}</div>' if note else ""
    return "".join(parts) + tail


def line_chart(series, *, height=320, kind="linear", invert=False, money=False, currency="USD",
               suffix="", digits=None, markers=True, note=""):
    """Multi-series line chart. invert=True reverses the axis (BSR: smaller is better)."""
    series = [s for s in series if s.get("values") and any(num(v) is not None for v in s["values"])]
    if not series:
        return ""
    if money and digits is None:
        digits = 2
    requested_log = kind == "log"

    labels = series[0].get("labels") or []
    points_count = max(len(s["values"]) for s in series)
    if points_count < 2:
        return ""

    all_values = [v for s in series for v in (num(x) for x in s["values"]) if v is not None]
    low, high = min(all_values), max(all_values)
    pad = (high - low) * 0.12 or max(abs(high) * 0.1, 1.0)
    low, high = low - pad, high + pad

    if kind == "log" and spans_a_decade(all_values):
        low, high = min(all_values) * 0.7, max(all_values) * 1.4
        ticks = log_ticks(low, high)
    else:
        kind = "linear"
        if requested_log:
            note = (note + "　" if note else "") + "数据跨度不足一个数量级，已改用线性轴。"
        ticks = [t for t in linear_ticks(low, high, 5) if low - 1e-9 <= t <= high + 1e-9]

    left, right, top = 74.0, SVG_W - 18.0, 22.0
    bottom = height - 52.0
    base_scale = make_scale(kind, low, high, top, bottom)

    def scale(value, _base=base_scale):
        if invert:
            return bottom - (_base(value) - top)
        return _base(value)

    parts = [svg_open(height)]
    for tick in ticks:
        y = scale(tick)
        if not (top - 1 <= y <= bottom + 1):
            continue
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="var(--muted)">{esc(axis_label(tick))}</text>'
        )

    plot_w = right - left
    step_x = plot_w / (points_count - 1)
    tick_every = max(1, math.ceil(points_count / 7))

    for s_index, item in enumerate(series):
        color = item.get("color") or CHART_COLORS[s_index % len(CHART_COLORS)]
        coords = []
        for index, raw_value in enumerate(item["values"]):
            value = num(raw_value)
            if value is None:
                continue
            coords.append((left + step_x * index, scale(value), value))
        if len(coords) < 2:
            continue
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in coords)
        parts.append(
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        if markers:
            for x, y, _ in coords:
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>')
        if len(coords) > 2:
            extremes = {min(coords, key=lambda c: c[2]), max(coords, key=lambda c: c[2])}
            for x, y, value in extremes:
                label = fmt(value, digits, money=money, currency=currency) + suffix
                anchor, dy = "middle", -9
                if x < left + 44:
                    anchor = "start"
                elif x > right - 44:
                    anchor = "end"
                if y < top + 20:
                    dy = 15
                parts.append(
                    f'<text x="{x:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" font-size="10.5" '
                    f'fill="{color}">{esc(label)}</text>'
                )

    for index in range(points_count):
        if index % tick_every and index != points_count - 1:
            continue
        x = left + step_x * index
        label = labels[index] if index < len(labels) else str(index + 1)
        parts.append(
            f'<text x="{x:.1f}" y="{bottom + 20:.1f}" text-anchor="middle" font-size="11" '
            f'fill="var(--muted)">{esc(clip(label, 12))}</text>'
        )

    parts.append("</svg>")
    body = "".join(parts)
    if len(series) > 1:
        legend = "".join(
            f'<span class="lg"><i style="background:{s.get("color") or CHART_COLORS[i % len(CHART_COLORS)]}"></i>'
            f'{esc(s.get("name", ""))}</span>'
            for i, s in enumerate(series)
        )
        body = f'<div class="legend">{legend}</div>' + body
    if note:
        body += f'<div class="chart-note">{esc(note)}</div>'
    return body


def grouped_bar_chart(categories, series, *, height=340, digits=None, money=False,
                      currency="USD", suffix="", note=""):
    categories = list(categories)
    series = [s for s in series if s.get("values")]
    if not categories or not series:
        return ""

    all_values = [v for s in series for v in (num(x) for x in s["values"]) if v is not None]
    if not all_values:
        return ""
    low = min(0.0, min(all_values) * 1.15)
    high = max(0.0, max(all_values) * 1.2)
    ticks = [t for t in linear_ticks(low, high, 5) if low - 1e-9 <= t <= high + 1e-9]

    left, right, top = 74.0, SVG_W - 18.0, 26.0
    bottom = height - 56.0
    scale = make_scale("linear", low, high, top, bottom)
    parts = [svg_open(height)]
    grid_and_axis(parts, ticks, scale, left, right)
    zero_y = scale(0.0) if low < 0 else scale(low)

    slot = (right - left) / len(categories)
    bar_w = min(slot * 0.7 / len(series), 34)
    rotate = max(text_width(c) for c in categories) > slot - 8

    for index, category in enumerate(categories):
        center = left + slot * index + slot / 2
        start = center - bar_w * len(series) / 2
        for s_index, item in enumerate(series):
            value = num(item["values"][index]) if index < len(item["values"]) else None
            if value is None:
                continue
            x = start + bar_w * s_index
            y = scale(value)
            y0, y1 = min(y, zero_y), max(y, zero_y)
            color = item.get("color") or CHART_COLORS[s_index % len(CHART_COLORS)]
            parts.append(
                f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bar_w - 2:.1f}" '
                f'height="{max(y1 - y0, 1.2):.1f}" rx="3" fill="{color}"/>'
            )
            label = fmt(value, digits, money=money, currency=currency) + suffix
            parts.append(
                f'<text x="{x + bar_w / 2 - 1:.1f}" y="{y0 - 5:.1f}" text-anchor="middle" '
                f'font-size="10.5" fill="var(--text2)">{esc(label)}</text>'
            )
        if rotate:
            anchor_y = bottom + 14
            parts.append(
                f'<text x="{center:.1f}" y="{anchor_y:.1f}" text-anchor="end" font-size="11" '
                f'fill="var(--muted)" transform="rotate(-35 {center:.1f} {anchor_y:.1f})">'
                f"{esc(clip(category, 16))}</text>"
            )
        else:
            parts.append(
                f'<text x="{center:.1f}" y="{bottom + 18:.1f}" text-anchor="middle" font-size="11" '
                f'fill="var(--muted)">{esc(clip(category, 16))}</text>'
            )

    parts.append("</svg>")
    legend = "".join(
        f'<span class="lg"><i style="background:{s.get("color") or CHART_COLORS[i % len(CHART_COLORS)]}"></i>'
        f'{esc(s.get("name", ""))}</span>'
        for i, s in enumerate(series)
    )
    body = f'<div class="legend">{legend}</div>' + "".join(parts)
    if note:
        body += f'<div class="chart-note">{esc(note)}</div>'
    return body


def bubble_chart(points, *, height=380, x_digits=2, y_digits=1, x_label="", y_label="",
                 size_label="", note=""):
    points = [p for p in points if num(p.get("x")) is not None and num(p.get("y")) is not None]
    if len(points) < 2:
        return ""

    xs = [num(p["x"]) for p in points]
    ys = [num(p["y"]) for p in points]
    sizes = [num(p.get("size")) or 1.0 for p in points]
    max_size = max(sizes) or 1.0

    left, right, top = 74.0, SVG_W - 26.0, 26.0
    bottom = height - 56.0
    x_low, x_high = min(xs), max(xs)
    x_pad = (x_high - x_low) * 0.15 or max(abs(x_high) * 0.1, 1.0)
    x_low, x_high = x_low - x_pad, x_high + x_pad
    y_low, y_high = min(ys), max(ys)
    y_pad = (y_high - y_low) * 0.2 or 0.2
    y_low, y_high = y_low - y_pad, y_high + y_pad

    scale_x = make_scale_x(x_low, x_high, left, right)
    scale_y = make_scale("linear", y_low, y_high, top, bottom)
    parts = [svg_open(height)]
    grid_and_axis(parts, [t for t in linear_ticks(y_low, y_high, 4) if y_low <= t <= y_high],
                  scale_y, left, right)
    for tick in [t for t in linear_ticks(x_low, x_high, 5) if x_low <= t <= x_high]:
        x = scale_x(tick)
        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" '
            f'stroke="var(--grid)" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{bottom + 20:.1f}" text-anchor="middle" font-size="11" '
            f'fill="var(--muted)">{esc(axis_label(tick))}</text>'
        )

    median_x = sorted(xs)[len(xs) // 2]
    median_y = sorted(ys)[len(ys) // 2]
    parts.append(
        f'<line x1="{scale_x(median_x):.1f}" y1="{top}" x2="{scale_x(median_x):.1f}" '
        f'y2="{bottom}" stroke="var(--axis)" stroke-width="1" stroke-dasharray="5 4"/>'
    )
    parts.append(
        f'<line x1="{left}" y1="{scale_y(median_y):.1f}" x2="{right}" '
        f'y2="{scale_y(median_y):.1f}" stroke="var(--axis)" stroke-width="1" stroke-dasharray="5 4"/>'
    )

    for point in points:
        x, y = scale_x(num(point["x"])), scale_y(num(point["y"]))
        radius = 5 + 16 * math.sqrt((num(point.get("size")) or 1.0) / max_size)
        highlight = bool(point.get("highlight"))
        fill = "var(--accent)" if highlight else CHART_COLORS[1]
        opacity = 0.55 if highlight else 0.34
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" '
            f'fill-opacity="{opacity}" stroke="{fill}" stroke-width="1.8"/>'
        )
        weight = 700 if highlight else 400
        parts.append(
            f'<text x="{x:.1f}" y="{y - radius - 5:.1f}" text-anchor="middle" font-size="10.5" '
            f'fill="var(--text2)" font-weight="{weight}">{esc(clip(point.get("label", ""), 12))}</text>'
        )

    if x_label:
        parts.append(
            f'<text x="{(left + right) / 2:.1f}" y="{height - 12:.1f}" text-anchor="middle" '
            f'font-size="11.5" fill="var(--muted)">{esc(x_label)}</text>'
        )
    if y_label:
        mid = (top + bottom) / 2
        parts.append(
            f'<text x="14" y="{mid:.1f}" text-anchor="middle" font-size="11.5" '
            f'fill="var(--muted)" transform="rotate(-90 14 {mid:.1f})">{esc(y_label)}</text>'
        )
    parts.append("</svg>")
    body = "".join(parts)
    caption = f"虚线为样本中位线（价格 {fmt(median_x, x_digits)}，评分 {fmt(median_y, y_digits)}）"
    if size_label:
        caption += f"；气泡大小 = {size_label}"
    body += f'<div class="chart-note">{esc(caption)}</div>'
    if note:
        body += f'<div class="chart-note">{esc(note)}</div>'
    return body


# ---------------------------------------------------------------- html pieces

PRIORITY_CLASS = {"P0": "high", "P1": "mid", "P2": "low", "高": "high", "中": "mid", "低": "low"}
CONFIDENCE_CLASS = {"高": "high", "中": "mid", "低": "low",
                    "high": "high", "medium": "mid", "low": "low"}


def delta_html(delta, better="higher", unit="%", digits=1):
    value = num(delta)
    if value is None:
        return ""
    if abs(value) <= 0.05:
        return '<span class="delta flat">● 持平</span>'
    direction = "up" if value > 0 else "down"
    arrow = "▲" if direction == "up" else "▼"
    if better in ("neutral", "none"):
        return f'<span class="delta flat">{arrow} {abs(value):.{digits}f}{unit}</span>'
    good = (direction == "up") if better != "lower" else (direction == "down")
    return f'<span class="delta {"up" if good else "down"}">{arrow} {abs(value):.{digits}f}{unit}</span>'


def kv_table(pairs, columns=2):
    rows = [p for p in pairs if p is not None]
    if not rows:
        return ""
    out = []
    index = 0
    while index < len(rows):
        cells = ""
        for _ in range(columns):
            if index < len(rows):
                label, value = rows[index]
                cells += f'<th scope="row">{esc(label)}</th><td>{value}</td>'
            else:
                cells += "<th></th><td></td>"
            index += 1
        out.append(f"<tr>{cells}</tr>")
    return f'<table class="kv">{"".join(out)}</table>'


def kv_pairs(pairs, empty="—"):
    """Build (label, html-value) pairs, skipping entries whose value is missing."""
    out = []
    for label, value in pairs:
        text = value if isinstance(value, str) else fmt(value)
        if text == "" or text == empty:
            continue
        out.append((label, esc(text)))
    return out


def theme_list(items, empty_label="暂无"):
    items = [i for i in items if i]
    if not items:
        return f'<p class="muted">{esc(empty_label)}</p>'
    lis = ""
    for item in items:
        pct = fmt_pct(item.get("pct"), 0) if num(item.get("pct")) is not None else ""
        badge = f' <span class="pct">{esc(pct)}</span>' if pct else ""
        evidence = f'<div class="sub">{esc(item["evidence"])}</div>' if item.get("evidence") else ""
        lis += f'<li>{esc(item.get("theme", ""))}{badge}{evidence}</li>'
    return f'<ul class="clean">{lis}</ul>'


def bullets(items, cls=""):
    texts = []
    for item in items:
        if not item:
            continue
        texts.append(item.get("text") or item.get("name") or "" if isinstance(item, dict) else item)
    if not texts:
        return ""
    lis = "".join(f"<li>{esc(text)}</li>" for text in texts)
    return f'<ul class="clean {cls}">{lis}</ul>'


def median(values):
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    middle = len(clean) // 2
    return clean[middle] if len(clean) % 2 else (clean[middle - 1] + clean[middle]) / 2


# ---------------------------------------------------------------- report shell

class Report:
    def __init__(self, data):
        self.data = data
        self.index = 0
        self.parts = []
        self.rendered = []
        self.chart_count = 0
        self.currency = (data.get("meta") or {}).get("currency") or "USD"

    def section(self, title, body):
        if not body or not body.strip():
            return
        self.index += 1
        self.chart_count += body.count("<svg")
        self.rendered.append(title)
        self.parts.append(
            f'<section class="card"><h2><span class="num">{self.index}</span>{esc(title)}</h2>'
            f"{body}</section>"
        )

    def html(self):
        return "".join(self.parts)


def render_header(data, gaps_count):
    meta = data.get("meta") or {}
    snap = data.get("snapshot") or {}
    fields = [
        ("ASIN", meta.get("asin")),
        ("站点", meta.get("marketplace", "US")),
        ("品牌", meta.get("brand")),
        ("类目", meta.get("category")),
        ("币种", meta.get("currency", "USD")),
        ("数据窗口", meta.get("dataWindow")),
        ("快照时间", meta.get("snapshotTime")),
    ]
    grid = "".join(
        f'<div class="meta-item"><span class="k">{esc(k)}</span>'
        f'<span class="v">{esc(v if v not in (None, "") else "—")}</span></div>'
        for k, v in fields
    )
    warn = ""
    if snap.get("returnBadge"):
        warn += f'<div class="head-warn">⚠ {esc(return_badge_text(snap))}</div>'
    if gaps_count:
        warn += (f'<div class="head-warn">⚠ {gaps_count} 项数据缺口未解决，'
                 "详见报告末尾「数据质量与缺口」</div>")
    subtitle = meta.get("title") or "Amazon 产品运营分析报告"
    sub_line = meta.get("subCategory") or ""
    return (
        '<header class="top"><h1>Amazon 产品运营分析报告</h1>'
        f'<div class="head-sub">{esc(subtitle)}'
        + (f' ｜ {esc(sub_line)}' if sub_line else "")
        + f'</div><div class="meta-grid">{grid}</div>{warn}</header>'
    )


# ---------------------------------------------------------------- sections

def return_badge_text(snap):
    """Amazon's return-rate warning, e.g. "Frequently returned item"."""
    badge = snap.get("returnBadge")
    if not badge:
        return ""
    if isinstance(badge, str):
        return badge
    return "亚马逊在商品页展示「经常退货」（Frequently returned item）标记"


def sec_summary(report, summary):
    if not summary:
        return
    body = []
    if summary.get("headline"):
        body.append(f'<div class="headline">{esc(summary["headline"])}</div>')

    key_numbers = summary.get("keyNumbers") or []
    if key_numbers:
        cards = []
        for item in key_numbers:
            delta = delta_html(item.get("delta"), item.get("better", "higher"), item.get("unit", "%"))
            hint = f'<div class="l">{esc(item["hint"])}</div>' if item.get("hint") else ""
            cards.append(
                f'<div class="kpi"><div class="v">{esc(item.get("value", "—"))}</div>'
                f'<div class="lb">{esc(item.get("label", ""))}</div>{delta}{hint}</div>'
            )
        body.append(f'<div class="kpis">{"".join(cards)}</div>')

    if summary.get("insights"):
        body.append('<h3 class="sub-h">关键洞察</h3>' + bullets(summary["insights"]))

    actions = summary.get("actions") or []
    if actions:
        rows = ""
        for action in actions:
            priority = str(action.get("priority", ""))
            rows += (
                f'<tr><td><span class="pill {PRIORITY_CLASS.get(priority, "mid")}">'
                f'{esc(priority or "—")}</span></td>'
                f'<td class="left">{esc(action.get("action", ""))}</td>'
                f'<td class="left muted">{esc(action.get("rationale", ""))}</td>'
                f'<td class="left muted">{esc(action.get("expectedImpact", ""))}</td></tr>'
            )
        body.append(
            '<h3 class="sub-h">行动建议</h3><div class="tw"><table>'
            "<tr><th>优先级</th><th>动作</th><th>依据</th><th>预期影响</th></tr>"
            f"{rows}</table></div>"
        )

    if summary.get("risks"):
        body.append('<div class="callout"><div class="callout-h">风险提示</div>'
                    + bullets(summary["risks"]) + "</div>")

    report.section("执行摘要", "".join(body))


def sec_overview(report, data):
    snap = data.get("snapshot") or {}
    if not snap:
        return
    cur = report.currency
    pairs = [
        ("当前售价", fmt(snap.get("price"), 2, money=True, currency=cur)),
        ("标价", fmt(snap.get("listPrice"), 2, money=True, currency=cur)),
        ("平均星级", fmt(snap.get("rating"), 2)),
        ("评论总数", fmt_int(snap.get("reviewCount"))),
        ("BSR（类目）", fmt_int(snap.get("bsr"))),
        ("BSR 子类目", fmt_int(snap.get("subCategoryRank"))),
        ("类目名称", snap.get("bsrCategory")),
        ("变体数", fmt_int(snap.get("variants"))),
        ("配送方式", snap.get("fulfillment")),
        ("优惠券 / 促销", snap.get("coupon")),
        ("问答数", fmt_int(snap.get("qa"))),
        ("首次上架", snap.get("firstAvailable")),
        ("卖家", snap.get("seller")),
    ]
    low, high = num(snap.get("variantPriceMin")), num(snap.get("variantPriceMax"))
    if low is not None or high is not None:
        pairs.append(("变体价带", f"{fmt(low, 2, money=True, currency=cur)} – "
                                f"{fmt(high, 2, money=True, currency=cur)}"))
    body = [kv_table(kv_pairs(pairs), 2)]
    if snap.get("returnBadge"):
        body.append(
            '<div class="callout warn"><div class="callout-h">⚠ 退货风险标记</div>'
            f'<p>{esc(return_badge_text(snap))}</p></div>'
        )

    flags = []
    if snap.get("returnBadge"):
        flags.append('<span class="flag warn">⚠ 经常退货（Frequently returned item）</span>')
    if snap.get("images") is not None:
        count = num(snap["images"]) or 0
        ok = count >= 6
        flags.append(
            f'<span class="flag {"ok" if ok else "warn"}">{"✓" if ok else "!"} 主图 {int(count)} 张'
            f'{"（建议 ≥ 6 张）" if not ok else ""}</span>'
        )
    for key, label in (("hasAplus", "A+ 页面"), ("hasVideo", "主图视频")):
        if snap.get(key) is not None:
            ok = bool(snap[key])
            flags.append(
                f'<span class="flag {"ok" if ok else "warn"}">{"✓" if ok else "✗"} {label}'
                f'{"（缺失）" if not ok else ""}</span>'
            )
    if snap.get("bulletCount") is not None:
        count = num(snap["bulletCount"]) or 0
        ok = count >= 5
        flags.append(
            f'<span class="flag {"ok" if ok else "warn"}">{"✓" if ok else "!"} 五点描述 {int(count)} 条'
            f'{"（建议补满 5 条）" if not ok else ""}</span>'
        )
    if flags:
        body.append('<h3 class="sub-h">Listing 完整度</h3><div class="flags">'
                    + "".join(flags) + "</div>")
    listing = data.get("listing") or {}
    if listing.get("notes"):
        body.append(bullets(listing["notes"]))
    report.section("产品概览", "".join(body))


def sec_price(report, data):
    price = data.get("price") or {}
    if not price:
        return
    cur = report.currency
    body = []
    pairs = kv_pairs([
        ("当前价", fmt(price.get("current"), 2, money=True, currency=cur)),
        ("标价", fmt(price.get("listPrice"), 2, money=True, currency=cur)),
        ("近 30 天均价", fmt(price.get("avg30"), 2, money=True, currency=cur)),
        ("区间最低", fmt(price.get("min"), 2, money=True, currency=cur)),
        ("区间最高", fmt(price.get("max"), 2, money=True, currency=cur)),
    ])
    if pairs:
        body.append(kv_table(pairs, 2))

    series = price.get("series") or []
    if len(series) >= 2:
        values = [num(p.get("price")) for p in series]
        clean = [v for v in values if v is not None]
        note = ""
        if clean:
            note = (f"区间最低 {fmt(min(clean), 2, money=True, currency=cur)} / "
                    f"最高 {fmt(max(clean), 2, money=True, currency=cur)}")
        body.append(line_chart(
            [{"name": "价格", "labels": [str(p.get("date", "")) for p in series], "values": values}],
            money=True, currency=cur, height=300, note=note,
        ))

    promos = price.get("promotions") or []
    if promos:
        rows = "".join(
            f'<tr><td>{esc(p.get("period", "—"))}</td><td>{esc(p.get("type", "—"))}</td>'
            f'<td>{esc(p.get("priceEffect", "—"))}</td></tr>'
            for p in promos
        )
        body.append('<h3 class="sub-h">促销记录</h3><div class="tw"><table>'
                    "<tr><th>时间</th><th>类型</th><th>价格影响</th></tr>" + rows + "</table></div>")
    if price.get("note"):
        body.append(f'<div class="chart-note">{esc(price["note"])}</div>')
    report.section("价格与促销", "".join(body))


def sec_rank_sales(report, data):
    rank = data.get("rank") or {}
    sales = data.get("sales") or {}
    if not rank and not sales:
        return
    cur = report.currency
    body = []

    series = rank.get("series") or []
    if len(series) >= 2:
        values = [num(p.get("rank")) for p in series]
        clean = [v for v in values if v is not None]
        direction = ""
        if len(clean) >= 2:
            change = (clean[0] - clean[-1]) / clean[0] * 100 if clean[0] else 0
            direction = f"区间变化 {change:+.1f}%（{'排名提升' if change > 0 else '排名下滑'}）"
        body.append(line_chart(
            [{"name": "BSR", "labels": [str(p.get("date", "")) for p in series], "values": values}],
            invert=True, height=300, digits=0,
            note=f"纵轴已反向：曲线越高代表排名越靠前。{direction}",
        ))
    elif rank.get("current") is not None:
        body.append(kv_table(kv_pairs([
            ("当前 BSR", fmt_int(rank.get("current"))),
            ("区间最佳", fmt_int(rank.get("best"))),
            ("区间最差", fmt_int(rank.get("worst"))),
            ("类目", rank.get("category")),
        ]), 2))

    monthly = sales.get("monthly") or []
    if monthly:
        labels = [str(m.get("month", "")) for m in monthly]
        body.append(bar_chart(
            labels, [m.get("units") for m in monthly], height=290, digits=0, suffix=" 件",
            highlight=len(monthly) - 1, note="月销量（单位：件）",
        ))
        revenues = [num(m.get("revenue")) for m in monthly]
        if any(v is not None for v in revenues):
            body.append(bar_chart(
                labels, revenues, height=280, money=True, currency=cur,
                highlight=len(monthly) - 1, note="月度 GMV",
            ))
    if sales.get("method") or sales.get("confidence"):
        body.append(
            '<div class="callout"><div class="callout-h">估算口径</div>'
            f'<p>方法：{esc(sales.get("method") or "—")}｜'
            f'置信度：{esc(sales.get("confidence") or "—")}</p></div>'
        )
    report.section("排名与销量", "".join(body))


def sec_reviews(report, data):
    reviews = data.get("reviews") or {}
    if not reviews:
        return
    body = []
    pairs = kv_pairs([
        ("平均星级", fmt(reviews.get("rating"), 2)),
        ("评论总数", fmt_int(reviews.get("count"))),
        ("近 30 天新增", fmt_int(reviews.get("newLast30d"))),
        ("近 30 天均分", fmt(reviews.get("ratingLast30d"), 2)),
        ("样本量", fmt_int(reviews.get("sampleSize"))),
    ])
    if pairs:
        body.append(kv_table(pairs, 2))

    dist = reviews.get("starDistribution") or {}
    stars = [("5", "5★"), ("4", "4★"), ("3", "3★"), ("2", "2★"), ("1", "1★")]
    if any(num(dist.get(k)) is not None for k, _ in stars):
        body.append(bar_chart(
            [label for _, label in stars], [dist.get(k) for k, _ in stars],
            height=290, digits=1, suffix="%",
            colors=["var(--good)", "var(--s4)", "var(--warn)", "var(--s5)", "var(--bad)"],
            note="星级分布；1★ 占比决定差评治理的优先级",
        ))

    history = reviews.get("history") or []
    if len(history) >= 2:
        labels = [str(h.get("date", "")) for h in history]
        body.append(line_chart(
            [{"name": "评论数", "labels": labels,
              "values": [h.get("count") for h in history], "color": "var(--s2)"}],
            height=290, kind="log", note="评论累计增长（对数轴，便于看清量级差距）",
        ))
        ratings = [num(h.get("rating")) for h in history]
        if any(v is not None for v in ratings):
            body.append(line_chart(
                [{"name": "评分", "labels": labels, "values": ratings, "color": "var(--s1)"}],
                height=270, digits=2, note="评分随时间变化；下滑要结合差评爆发时间点判断",
            ))

    positives = reviews.get("positiveThemes") or []
    negatives = reviews.get("negativeThemes") or []
    if positives or negatives:
        body.append(
            '<div class="grid2">'
            f'<div class="panel good"><div class="panel-h">👍 正向主题</div>{theme_list(positives)}</div>'
            f'<div class="panel bad"><div class="panel-h">👎 负向痛点</div>{theme_list(negatives)}</div>'
            "</div>"
        )
    if reviews.get("trend"):
        body.append(f'<div class="chart-note">评分走势：{esc(reviews["trend"])}</div>')
    report.section("评论与口碑", "".join(body))


def sec_traffic(report, data):
    traffic = data.get("traffic") or {}
    if not traffic:
        return
    body = []
    pairs = kv_pairs([
        ("会话数", fmt_int(traffic.get("sessions"))),
        ("转化率", fmt_pct(traffic.get("conversion"))),
        ("自然流量占比", fmt_pct(traffic.get("naturalShare"), 0)),
        ("广告流量占比", fmt_pct(traffic.get("adShare"), 0)),
        ("ACOS", fmt_pct(traffic.get("acos"))),
        ("TACOS", fmt_pct(traffic.get("tacos"))),
        ("广告销售占比", fmt_pct(traffic.get("adSalesShare"), 0)),
    ])
    if pairs:
        body.append(kv_table(pairs, 2))

    natural, ad = num(traffic.get("naturalShare")), num(traffic.get("adShare"))
    if natural is not None and ad is not None:
        body.append(bar_chart(
            ["自然流量", "广告流量"], [natural, ad], height=230, digits=0, suffix="%",
            colors=["var(--s4)", "var(--s1)"],
            note="流量结构：广告占比过高时，停投即掉量的风险大",
        ))

    keywords = [k for k in (traffic.get("keywords") or []) if k.get("keyword")]
    if keywords:
        keywords = sorted(keywords, key=lambda k: num(k.get("trafficShare")) or 0, reverse=True)[:10]
        body.append(hbar_chart(
            [k.get("keyword") for k in keywords], [k.get("trafficShare") for k in keywords],
            digits=1, suffix="%", note="各搜索词带来的流量占比（Top 10）",
        ))
        rows = "".join(
            f'<tr><td class="left">{esc(k.get("keyword"))}</td>'
            f'<td>{fmt_int(k.get("searchVolume"))}</td><td>{fmt_int(k.get("ourRank"))}</td>'
            f'<td>{fmt_pct(k.get("trafficShare"))}</td><td>{fmt_pct(k.get("clickShare"))}</td>'
            f'<td>{fmt_pct(k.get("conversionShare"))}</td></tr>'
            for k in keywords
        )
        body.append(
            '<h3 class="sub-h">关键词明细</h3><div class="tw"><table>'
            "<tr><th>关键词</th><th>月搜索量</th><th>本 ASIN 排名</th><th>流量占比</th>"
            "<th>点击份额</th><th>转化份额</th></tr>" + rows + "</table></div>"
        )
    if traffic.get("note"):
        body.append(f'<div class="chart-note">{esc(traffic["note"])}</div>')
    report.section("流量与关键词", "".join(body))


def sec_competitors(report, data):
    competitors = [c for c in (data.get("competitors") or []) if c]
    if not competitors:
        return
    meta = data.get("meta") or {}
    snap = data.get("snapshot") or {}
    cur = report.currency
    target = meta.get("asin") or "本 ASIN"

    def label_for(item, fallback):
        asin = item.get("asin") or fallback
        brand = (item.get("brand") or "").strip()
        return f"{brand}\n{asin}" if brand else str(asin)

    labels = [f"{target}\n（目标）"] + [
        label_for(c, f"竞品{i + 1}") for i, c in enumerate(competitors)
    ]
    header_labels = [f'{esc(target)}<br><span class="sub">（目标／{esc(meta.get("brand", ""))}）</span>'
                     if meta.get("brand") else f'{esc(target)}<br><span class="sub">（目标）</span>'] + [
        (f'{esc(c.get("brand"))}<br><span class="sub">{esc(c.get("asin") or "")}</span>'
         if (c.get("brand") or "").strip()
         else f'{esc(c.get("asin") or f"竞品{i + 1}")}')
        for i, c in enumerate(competitors)
    ]

    subject_price = num((data.get("price") or {}).get("current")) or num(snap.get("price"))
    subject_rating = num((data.get("reviews") or {}).get("rating")) or num(snap.get("rating"))
    subject_reviews = num((data.get("reviews") or {}).get("count")) or num(snap.get("reviewCount"))
    subject_bsr = num((data.get("rank") or {}).get("current")) or num(snap.get("bsr"))

    prices = [subject_price] + [num(c.get("price")) for c in competitors]
    ratings = [subject_rating] + [num(c.get("rating")) for c in competitors]
    review_counts = [subject_reviews] + [num(c.get("reviewCount")) for c in competitors]
    bsrs = [subject_bsr] + [num(c.get("bsr")) for c in competitors]
    median_price = median(prices[1:])

    metrics = [
        ("价格", prices, lambda v: fmt(v, 2, money=True, currency=cur)),
        ("平均星级", ratings, lambda v: fmt(v, 2)),
        ("评论总数", review_counts, lambda v: fmt_int(v)),
        ("BSR", bsrs, lambda v: fmt_int(v)),
        ("月销估算", [None] + [num(c.get("monthlyUnits")) for c in competitors], lambda v: fmt_int(v)),
        ("变体数", [None] + [num(c.get("variants")) for c in competitors], lambda v: fmt_int(v)),
    ]

    head = '<tr><th>指标</th>' + "".join(
        f'<th class="{"target-col" if i == 0 else ""}">{name}</th>'
        for i, name in enumerate(header_labels)
    ) + '<th class="bench-col">竞品中位</th></tr>'
    rows = ""
    for name, values, formatter in metrics:
        if not any(v is not None for v in values[1:]):
            continue
        cells = "".join(
            f'<td class="{"target-col" if i == 0 else ""}">{esc(formatter(v))}</td>'
            for i, v in enumerate(values)
        )
        rows += (f'<tr><td class="left">{esc(name)}</td>{cells}'
                 f'<td class="bench-col">{esc(formatter(median(values[1:])))}</td></tr>')

    body = [f'<div class="tw"><table>{head}{rows}</table></div>']
    body.append(
        '<div class="chart-note">注：竞品列头为「品牌 / ASIN」，图表横轴第一行为品牌、第二行为 ASIN；'
        'BSR 数值越小代表排名越靠前；评论总数反映"评论资产／社交证明"；'
        '"竞品中位"为除本 ASIN 之外竞品的中位数。</div>'
    )
    chart_specs = [
        ("价格", prices, dict(height=300, money=True, currency=cur, ref=median_price,
                             ref_label="竞品中位价", note="价格对比：柱越低越便宜；虚线为竞品中位价")),
        ("平均星级", ratings, dict(height=300, digits=2, zero_base=False,
                                note="星级对比：差距要结合评论数看，样本不足时星级参考价值有限")),
        ("评论总数", review_counts, dict(height=300, kind="log", digits=0,
                                    note="评论量级对比（对数轴）：反映评论资产的差距倍数")),
        ("BSR", bsrs, dict(height=300, digits=0,
                          note="BSR 对比：数值越小排名越靠前，条越短越靠前")),
    ]
    skipped = [name for name, values, _ in chart_specs if not any(v is not None for v in values[1:])]
    for name, values, options in chart_specs:
        if any(v is not None for v in values[1:]):
            body.append(bar_chart(labels, values, **options))
    if skipped:
        body.append(
            f'<div class="chart-note">未做横向对比的指标：{"、".join(skipped)}'
            "（未取得竞品数据，不做只有本 ASIN 一根柱子的伪对比，缺口见「数据质量与缺口」）</div>"
        )

    points = []
    if subject_price is not None and subject_rating is not None:
        points.append({
            "label": target, "x": subject_price, "y": subject_rating,
            "size": subject_reviews or 1, "highlight": True,
        })
    for competitor in competitors:
        if num(competitor.get("price")) is None or num(competitor.get("rating")) is None:
            continue
        points.append({
            "label": (competitor.get("brand") or competitor.get("asin") or "竞品"),
            "x": num(competitor["price"]),
            "y": num(competitor["rating"]),
            "size": num(competitor.get("reviewCount")) or 1,
        })
    if len(points) >= 2:
        body.append(bubble_chart(
            points, x_label=f"价格（{cur}）", y_label="平均星级", size_label="评论数",
            note="定位图：左上＝便宜且高分（理想区），右下＝偏贵且口碑弱（风险区）。"
                 "气泡标签为品牌名，对应 ASIN 见上方对比表。",
        ))
    report.section("竞品对比（横向）", "".join(body))


def sec_benchmark(report, data):
    benchmark = data.get("benchmark") or {}
    rows_data = [r for r in (benchmark.get("rows") or []) if r]
    if not rows_data:
        return
    cur = report.currency
    body = []
    if benchmark.get("label"):
        body.append(f'<div class="chart-note">基准定义：{esc(benchmark["label"])}</div>')

    rows = ""
    gap_labels, gap_values = [], []
    for row in rows_data:
        subject, base = num(row.get("subject")), num(row.get("benchmark"))
        better = row.get("better", "higher")
        tolerance = num(row.get("tolerance"))
        money = str(row.get("unit", "")).upper() in CUR_SYMBOL
        unit = str(row.get("unit", "")).upper() if money else row.get("unit", "")

        def show(value, _money=money, _unit=unit):
            if _money:
                return fmt(value, 2, money=True, currency=_unit)
            if str(_unit) == "%":
                return fmt(value, 1) + "%"
            text = fmt(value)
            return f"{text} {_unit}" if _unit else text

        if subject is None or base is None or base == 0:
            gap, judgement = "—", ""
        else:
            change = (subject - base) / abs(base) * 100
            gap = f"{change:+.1f}%"
            if better in ("neutral", "none"):
                judgement = '<span class="pill mid">定位参考</span>'
            else:
                on_par = abs(subject - base) <= tolerance if tolerance is not None else abs(change) <= 10
                if on_par:
                    judgement = '<span class="pill mid">持平</span>'
                else:
                    good = change > 0 if better != "lower" else change < 0
                    judgement = (f'<span class="pill {"low" if good else "high"}">'
                                 f'{"达标" if good else "未达标"}</span>')
            gap_labels.append(str(row.get("metric", "")))
            gap_values.append(change)
        rows += (
            f'<tr><td class="left">{esc(row.get("metric", ""))}</td>'
            f'<td>{esc(show(subject))}</td><td>{esc(show(base))}</td>'
            f'<td>{esc(gap)}</td><td>{judgement}</td></tr>'
        )
    body.append(
        '<div class="tw"><table><tr><th>指标</th><th>本 ASIN</th><th>品类基准</th>'
        f"<th>差距</th><th>判定</th></tr>{rows}</table></div>"
    )
    if gap_values:
        body.append(bar_chart(
            gap_labels, gap_values, height=300, digits=1, suffix="%", highlight=-1,
            note="相对品类基准的差距百分比：正数高于基准，负数低于基准"
                 "（BSR 请按「越小越好」解读，正数代表排名更靠后）",
        ))
    report.section("品类基准达标", "".join(body))


def sec_trend_compare(report, data):
    compare = data.get("trendCompare") or {}
    rows_data = [r for r in (compare.get("rows") or []) if r]
    if not rows_data:
        return
    current_label = compare.get("currentLabel") or "本期"
    previous_label = compare.get("previousLabel") or "上期"
    body = []
    rows = ""
    delta_labels, delta_values, delta_colors = [], [], []

    for row in rows_data:
        current, previous = num(row.get("current")), num(row.get("previous"))
        better = row.get("better", "higher")
        unit = row.get("unit") or ""
        money = str(unit).upper() in CUR_SYMBOL
        change_html, change_value = "—", None
        if current is not None and previous not in (None, 0):
            change_value = (current - previous) / abs(previous) * 100
            change_html = delta_html(change_value, better, "%")

        def show(value, _money=money, _unit=str(unit).upper(), _raw=str(unit)):
            if _money:
                return fmt(value, 2, money=True, currency=_unit)
            if _raw == "%":
                return fmt(value, 1) + "%"
            text = fmt(value)
            return f"{text} {_raw}" if _raw else text

        rows += (
            f'<tr><td class="left">{esc(row.get("metric", ""))}</td>'
            f'<td>{esc(show(current))}</td><td>{esc(show(previous))}</td>'
            f'<td>{change_html}</td></tr>'
        )
        if change_value is not None:
            delta_labels.append(str(row.get("metric", "")))
            delta_values.append(change_value)
            good = change_value > 0 if better != "lower" else change_value < 0
            delta_colors.append("var(--good)" if good else "var(--bad)")

    body.append(
        f'<div class="tw"><table><tr><th>指标</th><th>{esc(current_label)}</th>'
        f"<th>{esc(previous_label)}</th><th>变化</th></tr>{rows}</table></div>"
    )
    if delta_values:
        body.append(bar_chart(
            delta_labels, delta_values, height=310, digits=1, suffix="%", colors=delta_colors,
            note="变化率：绿色＝朝好的方向变化，红色＝恶化（BSR 按「越小越好」判定）",
        ))
    report.section("纵向对比（本期 vs 上期）", "".join(body))


def sec_economics(report, data):
    econ = data.get("economics") or {}
    if not econ:
        return
    cur = econ.get("currency") or report.currency
    body = []
    pairs = kv_pairs([
        ("售价", fmt(econ.get("price"), 2, money=True, currency=cur)),
        ("单件毛利", fmt(econ.get("grossProfit"), 2, money=True, currency=cur)),
        ("毛利率", fmt_pct(econ.get("grossMargin"))),
        ("净利率", fmt_pct(econ.get("netMargin"))),
    ])
    if pairs:
        body.append(kv_table(pairs, 2))

    costs = [
        ("售价", num(econ.get("price")), "var(--accent)"),
        ("佣金", num(econ.get("referralFee")), "var(--bad)"),
        ("FBA 配送费", num(econ.get("fbaFee")), "var(--bad)"),
        ("采购成本", num(econ.get("cogs")), "var(--bad)"),
        ("头程物流", num(econ.get("firstLeg")), "var(--bad)"),
        ("单件广告", num(econ.get("adCostPerUnit")), "var(--bad)"),
        ("仓储费", num(econ.get("storage")), "var(--bad)"),
        ("其它成本", num(econ.get("other")), "var(--bad)"),
    ]
    costs = [c for c in costs if c[1] is not None]
    if len(costs) >= 3:
        body.append(hbar_chart(
            [label for label, _, _ in costs], [abs(v) for _, v, _ in costs],
            money=True, currency=cur, colors=[color for _, _, color in costs],
            label_width=150,
            note="成本结构（按绝对值横向对比）：佣金按售价比例计、FBA 按体积重量计，"
                 "均以官方费率为准；橙色为售价，红色为各项成本",
        ))
    if econ.get("note"):
        body.append(f'<div class="chart-note">{esc(econ["note"])}</div>')
    report.section("利润与成本", "".join(body))


def sec_inventory(report, data):
    inventory = data.get("inventory") or {}
    if not inventory:
        return
    body = []
    pairs = kv_pairs([
        ("可售库存", fmt_int(inventory.get("availableUnits"))),
        ("日均销量", fmt(inventory.get("dailySales"), 1)),
        ("可售天数", (fmt(inventory.get("daysOfCover"), 1) + " 天")
         if num(inventory.get("daysOfCover")) is not None else "—"),
        ("在途数量", fmt_int(inventory.get("inboundUnits"))),
        ("补货周期", (fmt(inventory.get("daysToRestock"), 0) + " 天")
         if num(inventory.get("daysToRestock")) is not None else "—"),
    ])
    if pairs:
        body.append(kv_table(pairs, 2))
    if inventory.get("risk"):
        cls = {"高": "high", "中": "mid", "低": "low"}.get(str(inventory["risk"]), "mid")
        body.append(
            '<div class="callout"><div class="callout-h">断货风险</div>'
            f'<p><span class="pill {cls}">{esc(inventory["risk"])}</span> '
            f'{esc(inventory.get("note", ""))}</p></div>'
        )
    elif inventory.get("note"):
        body.append(f'<div class="chart-note">{esc(inventory["note"])}</div>')
    report.section("库存与补货风险", "".join(body))


def sec_quality(report, data):
    sources = [s for s in (data.get("sources") or []) if s]
    gaps = [g for g in (data.get("gaps") or []) if g]
    if not sources and not gaps:
        return
    body = []
    if sources:
        rows = ""
        for source in sources:
            link = (f'<td class="left src"><a href="{esc(source.get("url"))}" target="_blank" '
                    f'rel="noopener">{esc(clip(source.get("url"), 46))}</a></td>'
                    if source.get("url") else "<td>—</td>")
            rows += (
                f'<tr><td class="left">{esc(source.get("name", "—"))}</td>'
                f'<td>{esc(source.get("type", "—"))}</td>'
                f'<td class="left muted">{esc(source.get("coverage", "—"))}</td>'
                f'<td>{esc(source.get("retrievedAt", "—"))}</td>'
                f'<td><span class="pill {CONFIDENCE_CLASS.get(str(source.get("confidence")), "mid")}">'
                f'{esc(source.get("confidence", "—"))}</span></td>{link}</tr>'
            )
        body.append(
            '<h3 class="sub-h">数据来源与置信度</h3><div class="tw"><table>'
            "<tr><th>来源</th><th>类型</th><th>覆盖字段</th><th>取数时间</th>"
            f"<th>置信度</th><th>链接</th></tr>{rows}</table></div>"
        )
    if gaps:
        items = "".join(f"<li>{esc(g)}</li>" for g in gaps)
        body.append(
            '<div class="callout warn"><div class="callout-h">数据缺口（影响结论可靠性）</div>'
            f'<ul class="clean">{items}</ul></div>'
        )
    report.section("数据质量与缺口", "".join(body))


def sec_methods(report, data):
    methods = [m for m in (data.get("methods") or []) if m]
    if not methods:
        return
    body = bullets(methods) + (
        '<div class="chart-note">估算值仅用于指示趋势与量级，不构成投资或采购决策依据；'
        "最终以官方报表数据为准。</div>"
    )
    report.section("方法与假设", body)


# ---------------------------------------------------------------- csv bundle

def write_csv_bundle(data, outdir):
    """Write the comparison tables and raw series as CSV (UTF-8 BOM for Excel)."""
    import csv

    meta = data.get("meta") or {}
    snap = data.get("snapshot") or {}
    cur = meta.get("currency") or "USD"
    asin = meta.get("asin") or "report"
    os.makedirs(outdir, exist_ok=True)
    written = []

    def dump(suffix, header, rows):
        if not rows:
            return
        path = os.path.join(outdir, f"amazon_{asin}_{suffix}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        written.append(path)

    summary = data.get("summary") or {}
    kpi_rows = [[item.get("label", ""), item.get("value", ""),
                 item.get("delta", ""), item.get("hint", "")]
                for item in (summary.get("keyNumbers") or [])]
    dump("kpi", ["指标", "数值", "变化", "说明"], kpi_rows)

    competitors = [c for c in (data.get("competitors") or []) if c]
    if competitors:
        target = f"{asin}（目标）"
        def csv_label(item, fallback):
            brand = (item.get("brand") or "").strip()
            ident = item.get("asin") or fallback
            return f"{brand} ({ident})" if brand else str(ident)

        labels = [target] + [csv_label(c, f"竞品{i + 1}") for i, c in enumerate(competitors)]
        subject_price = num((data.get("price") or {}).get("current")) or num(snap.get("price"))
        subject_rating = num((data.get("reviews") or {}).get("rating")) or num(snap.get("rating"))
        subject_reviews = num((data.get("reviews") or {}).get("count")) or num(snap.get("reviewCount"))
        subject_bsr = num((data.get("rank") or {}).get("current")) or num(snap.get("bsr"))
        rows = []
        for name, values in (
            ("价格", [subject_price] + [num(c.get("price")) for c in competitors]),
            ("平均星级", [subject_rating] + [num(c.get("rating")) for c in competitors]),
            ("评论总数", [subject_reviews] + [num(c.get("reviewCount")) for c in competitors]),
            ("BSR", [subject_bsr] + [num(c.get("bsr")) for c in competitors]),
            ("月销估算", [None] + [num(c.get("monthlyUnits")) for c in competitors]),
            ("变体数", [None] + [num(c.get("variants")) for c in competitors]),
        ):
            if not any(v is not None for v in values[1:]):
                continue
            rows.append([name] + ["" if v is None else f"{v:g}" for v in values]
                        + ["" if median(values[1:]) is None else f"{median(values[1:]):g}"])
        dump("competitors", ["指标"] + labels + ["竞品中位"], rows)

    benchmark_rows = []
    for row in (data.get("benchmark") or {}).get("rows") or []:
        subject, base = num(row.get("subject")), num(row.get("benchmark"))
        gap = "" if subject is None or not base else f"{(subject - base) / abs(base) * 100:.1f}%"
        benchmark_rows.append([row.get("metric", ""), row.get("subject", ""),
                               row.get("benchmark", ""), row.get("unit", ""),
                               gap, row.get("better", "higher")])
    label = (data.get("benchmark") or {}).get("label", "")
    dump("benchmark", ["指标", "本 ASIN", "品类基准", "单位", "差距", "方向", "基准定义"],
         [row + [label] for row in benchmark_rows])

    trend = data.get("trendCompare") or {}
    trend_rows = []
    for row in trend.get("rows") or []:
        current, previous = num(row.get("current")), num(row.get("previous"))
        change = "" if current is None or not previous else f"{(current - previous) / abs(previous) * 100:.1f}%"
        trend_rows.append([row.get("metric", ""), row.get("current", ""), row.get("previous", ""),
                           row.get("unit", ""), change, row.get("better", "higher")])
    dump("trend_compare", ["指标", trend.get("currentLabel", "本期"), trend.get("previousLabel", "上期"),
                           "单位", "变化", "方向"], trend_rows)

    keyword_rows = [[k.get("keyword", ""), k.get("searchVolume", ""), k.get("ourRank", ""),
                     k.get("trafficShare", ""), k.get("clickShare", ""), k.get("conversionShare", "")]
                    for k in (data.get("traffic") or {}).get("keywords") or []]
    dump("keywords", ["关键词", "月搜索量", "本 ASIN 排名", "流量占比(%)",
                      "点击份额(%)", "转化份额(%)"], keyword_rows)

    econ = data.get("economics") or {}
    econ_rows = [[key, econ[key]] for key in
                 ("price", "referralFee", "fbaFee", "cogs", "firstLeg", "adCostPerUnit",
                  "storage", "other", "grossProfit", "grossMargin", "netMargin")
                 if econ.get(key) is not None]
    dump("economics", [f"项目（币种 {econ.get('currency') or cur}）", "数值"], econ_rows)

    dump("price_series", ["日期", "价格"],
         [[p.get("date", ""), p.get("price", "")] for p in (data.get("price") or {}).get("series") or []])
    dump("bsr_series", ["日期", "BSR"],
         [[p.get("date", ""), p.get("rank", "")] for p in (data.get("rank") or {}).get("series") or []])
    dump("review_history", ["日期", "评论数", "评分"],
         [[h.get("date", ""), h.get("count", ""), h.get("rating", "")]
          for h in (data.get("reviews") or {}).get("history") or []])
    dump("sales_monthly", ["月份", "销量", "GMV"],
         [[m.get("month", ""), m.get("units", ""), m.get("revenue", "")]
          for m in (data.get("sales") or {}).get("monthly") or []])

    dump("gaps", ["数据缺口"], [[gap] for gap in data.get("gaps") or []])
    return written


# ---------------------------------------------------------------- page

CSS = """
:root{
  --bg:#f6f7f9; --card:#ffffff; --text:#1f2329; --text2:#3c4450; --muted:#6b7280;
  --border:#e5e7eb; --grid:#eceef1; --axis:#c9ced6;
  --accent:#ff9900; --accent2:#146eb4; --good:#16a34a; --bad:#dc2626; --warn:#d97706;
  --s1:#ff9900; --s2:#146eb4; --s3:#7c3aed; --s4:#0d9488; --s5:#db2777; --s6:#64748b;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0f1115; --card:#171a21; --text:#e6e8eb; --text2:#c6ccd3; --muted:#9aa3ad;
    --border:#2a2f3a; --grid:#242a35; --axis:#3a4250;
    --accent:#ffb340; --accent2:#4ea1ff; --good:#4ade80; --bad:#f87171; --warn:#fbbf24;
    --s1:#ffb340; --s2:#4ea1ff; --s3:#a78bfa; --s4:#2dd4bf; --s5:#f472b6; --s6:#94a3b8;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);line-height:1.62;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  padding:24px 18px 40px;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1080px;margin:0 auto}
header.top{background:linear-gradient(135deg,#ff9900,#146eb4);color:#fff;border-radius:16px;
  padding:26px 30px;margin-bottom:20px;box-shadow:0 6px 20px rgba(0,0,0,.08)}
header.top h1{margin:0;font-size:23px;line-height:1.35}
.head-sub{opacity:.92;font-size:13px;margin-top:5px}
.meta-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px 18px;
  margin-top:18px;border-top:1px solid rgba(255,255,255,.3);padding-top:14px}
.meta-item{font-size:12.5px;display:flex;flex-direction:column;gap:2px}
.meta-item .k{opacity:.85}
.meta-item .v{font-weight:600;word-break:break-word}
.head-warn{margin-top:14px;background:rgba(0,0,0,.16);border-radius:9px;padding:8px 12px;font-size:12.5px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px 24px;margin-bottom:18px}
.card h2{margin:0 0 16px;font-size:17.5px;display:flex;align-items:center;gap:9px;
  border-left:4px solid var(--accent);padding-left:11px}
.card h2 .num{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;
  border-radius:7px;background:var(--accent);color:#fff;font-size:12.5px;padding:0 5px}
.sub-h{margin:18px 0 8px;font-size:14.5px;color:var(--text2)}
.headline{font-size:16.5px;font-weight:600;margin-bottom:16px;line-height:1.72;
  border-left:3px solid var(--accent2);padding-left:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(156px,1fr));gap:12px;margin-bottom:6px}
.kpi{background:var(--bg);border:1px solid var(--border);border-radius:11px;padding:13px 14px}
.kpi .v{font-size:21px;font-weight:700;color:var(--accent2);line-height:1.25}
.kpi .lb{font-size:12px;color:var(--muted);margin-top:2px}
.kpi .l{font-size:11.5px;color:var(--muted);margin-top:5px;line-height:1.5}
.delta{display:inline-block;font-size:12px;margin-top:5px;font-weight:600}
.delta.up{color:var(--good)} .delta.down{color:var(--bad)} .delta.flat{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 11px;border-bottom:1px solid var(--border);text-align:center}
th{background:var(--bg);color:var(--muted);font-weight:600;font-size:12.5px}
th{white-space:nowrap}
td:first-child,th:first-child{text-align:left}
td.left{text-align:left}
tr:last-child td{border-bottom:none}
.kv th{width:20%;color:var(--muted);font-weight:500}
.target-col{background:rgba(255,153,0,.10);font-weight:600}
.bench-col{background:rgba(20,110,180,.07)}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
.chart{margin:10px 0 2px;display:block}
.chart-note{font-size:12px;color:var(--muted);margin:2px 0 10px;line-height:1.6}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--muted);margin:8px 0 0}
.legend .lg{display:inline-flex;align-items:center;gap:6px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.panel{border:1px solid var(--border);border-radius:11px;padding:13px 15px;background:var(--bg)}
.panel.good{border-left:3px solid var(--good)}
.panel.bad{border-left:3px solid var(--bad)}
.panel-h{font-size:13.5px;font-weight:600;margin-bottom:7px}
ul.clean{margin:6px 0;padding-left:19px;font-size:13.5px}
ul.clean li{margin-bottom:5px}
.pct{color:var(--accent2);font-weight:600;font-size:12.5px}
.sub{font-size:12px;color:var(--muted)}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11.5px;font-weight:600;white-space:nowrap}
.pill.high{background:rgba(220,38,38,.15);color:var(--bad)}
.pill.mid{background:rgba(217,119,6,.15);color:var(--warn)}
.pill.low{background:rgba(22,163,74,.15);color:var(--good)}
.flag{display:inline-block;padding:4px 10px;border-radius:8px;font-size:12.5px;margin:0 8px 8px 0;
  border:1px solid var(--border);background:var(--bg)}
.flag.ok{color:var(--good);border-color:rgba(22,163,74,.35)}
.flag.warn{color:var(--warn);border-color:rgba(217,119,6,.35)}
.flags{display:flex;flex-wrap:wrap}
.callout{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--accent2);
  border-radius:10px;padding:12px 15px;margin:12px 0;font-size:13.5px}
.callout.warn{border-left-color:var(--warn)}
.callout p{margin:0}
.callout-h{font-weight:600;margin-bottom:5px;font-size:13.5px}
.muted{color:var(--muted)}
.src a{color:var(--accent2);text-decoration:none;word-break:break-all}
.src a:hover{text-decoration:underline}
footer{text-align:center;color:var(--muted);font-size:12px;padding:16px 0 0;line-height:1.7}
@media print{
  body{background:#fff;padding:0}
  .card{break-inside:avoid;border:none;border-bottom:1px solid #ddd;border-radius:0;padding:12px 0}
  header.top{box-shadow:none;border-radius:0}
}
"""


def render(data):
    meta = data.get("meta") or {}
    summary = data.get("summary") or {}
    gaps = [g for g in (data.get("gaps") or []) if g]

    if not meta.get("asin"):
        raise SystemExit("ERROR: meta.asin is required.")
    if not summary.get("headline"):
        print("WARN: summary.headline 缺失，报告将缺少一句话结论（三要素之一）。", file=sys.stderr)

    report = Report(data)
    sec_summary(report, summary)
    sec_overview(report, data)
    sec_price(report, data)
    sec_rank_sales(report, data)
    sec_reviews(report, data)
    sec_traffic(report, data)
    sec_competitors(report, data)
    sec_benchmark(report, data)
    sec_trend_compare(report, data)
    sec_economics(report, data)
    sec_inventory(report, data)
    sec_quality(report, data)
    sec_methods(report, data)

    if not any(key in data for key in ("competitors", "benchmark", "trendCompare")):
        print("WARN: 缺少对比类数据（competitors / benchmark / trendCompare），"
              "「数据对比」要素不完整。", file=sys.stderr)
    if report.chart_count < 4:
        print(f"WARN: 仅渲染 {report.chart_count} 张图表，三要素要求至少 4 张。", file=sys.stderr)

    safe_json = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    footer_bits = [
        f'数据窗口 {meta.get("dataWindow") or "—"}',
        f"章节 {report.index} 个",
        f"图表 {report.chart_count} 张",
    ]
    if meta.get("generatedAt"):
        footer_bits.insert(0, f'生成时间 {meta["generatedAt"]}')

    document = (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>Amazon 运营分析报告 · {esc(meta.get("asin"))}</title>\n'
        f"<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">"
        + render_header(data, len(gaps))
        + report.html()
        + "<footer>"
        + f'Amazon 运营数据分析报告 ｜ ASIN {esc(meta.get("asin"))} ｜ 站点 {esc(meta.get("marketplace", "US"))}<br>'
        + " ｜ ".join(esc(bit) for bit in footer_bits)
        + "<br>数据快照时间见各章节标注；估算值请以官方报表复核。</footer>"
        + "</div>\n"
        + f'<script type="application/json" id="report-source-data">{safe_json}</script>\n'
        + "</body>\n</html>\n"
    )
    return document, report


def main():
    parser = argparse.ArgumentParser(
        description="Build a self-contained Amazon ASIN analysis report (HTML + inline SVG).")
    parser.add_argument("--data", required=True, help="path to the canonical analysis JSON")
    parser.add_argument("--out", required=True, help="path of the HTML report to write")
    parser.add_argument("--csv", help="directory for the CSV bundle (comparison tables + raw series)")
    parser.add_argument("--open", action="store_true", help="open the report in the default browser")
    args = parser.parse_args()

    data_path = os.path.expanduser(args.data)
    out_path = os.path.expanduser(args.out)
    with open(data_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    document, report = render(data)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(document)

    print(f"[OK] 报告已生成：{os.path.abspath(out_path)}")
    print(f"     章节 {report.index} 个，图表 {report.chart_count} 张")
    print("     章节：" + " / ".join(report.rendered))
    if args.csv:
        written = write_csv_bundle(data, os.path.expanduser(args.csv))
        print(f"     CSV {len(written)} 个 → {os.path.abspath(os.path.expanduser(args.csv))}")
        for path in written:
            print(f"       · {os.path.basename(path)}")
    if args.open:
        try:
            webbrowser.open("file://" + os.path.abspath(out_path))
        except Exception as exc:
            print(f"WARN: 自动打开失败（{exc}），请手动打开上面的路径。", file=sys.stderr)


if __name__ == "__main__":
    main()
