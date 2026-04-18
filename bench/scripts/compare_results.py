#!/usr/bin/env python3
"""跨模型对比报告工具。

读取 results/ 目录下的 merged_*.json 文件（或指定多个结果文件），
生成终端表格和可选的 Markdown 报告。

用法:
    # 自动对比所有 merged_*.json
    python compare_results.py

    # 指定文件
    python compare_results.py results/merged_a.json results/merged_b.json

    # 输出 Markdown 报告
    python compare_results.py --markdown report.md

    # 只对比特定分类
    python compare_results.py --category robot_query,task_create
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_results(paths: List[Path]) -> List[Dict[str, Any]]:
    results = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["_source"] = p.name
            results.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  跳过 {p.name}: {e}", file=sys.stderr)
    return results


def _short_model(model: str) -> str:
    """缩短模型名用于表格显示。"""
    parts = model.rsplit("/", 1)
    return parts[-1] if len(parts) > 1 else model


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "-"
    return f"{val:.1f}%"


def _fmt_tokens(val: int) -> str:
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)


def _fmt_time(seconds: float) -> str:
    if seconds >= 60:
        return f"{seconds / 60:.1f}m"
    return f"{seconds:.1f}s"


def _fmt_cost(val: float) -> str:
    if val == 0:
        return "-"
    return f"${val:.4f}"


def _pad(text: str, width: int, align: str = "left") -> str:
    # 中文字符占两个显示宽度
    display_width = sum(2 if ord(c) > 127 else 1 for c in text)
    padding = max(0, width - display_width)
    if align == "right":
        return " " * padding + text
    return text + " " * padding


def print_table(headers: List[str], rows: List[List[str]], col_aligns: Optional[List[str]] = None):
    """打印对齐的终端表格。"""
    if not rows:
        return
    col_aligns = col_aligns or ["left"] * len(headers)

    # 计算每列最大显示宽度
    widths = []
    for i, h in enumerate(headers):
        hw = sum(2 if ord(c) > 127 else 1 for c in h)
        max_w = hw
        for row in rows:
            if i < len(row):
                rw = sum(2 if ord(c) > 127 else 1 for c in row[i])
                max_w = max(max_w, rw)
        widths.append(max_w)

    def fmt_row(cells):
        parts = []
        for i, cell in enumerate(cells):
            align = col_aligns[i] if i < len(col_aligns) else "left"
            parts.append(_pad(cell, widths[i], align))
        return "  ".join(parts)

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def build_task_map(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """task_id -> task entry"""
    return {t["task_id"]: t for t in data.get("tasks", [])}


def compare_overall(results: List[Dict[str, Any]]):
    """总分对比表。"""
    print("\n📊 总分对比")
    print("=" * 60)

    headers = ["模型", "任务数", "总分", "得分率", "Tokens", "耗时", "费用"]
    rows = []
    for r in results:
        s = r.get("summary", {})
        e = r.get("efficiency", {})
        rows.append([
            _short_model(r.get("model", "?")),
            str(s.get("total_tasks", 0)),
            f"{s.get('total_score', 0):.1f}/{s.get('max_score', 0):.0f}",
            _fmt_pct(s.get("score_percentage")),
            _fmt_tokens(e.get("total_tokens", 0)),
            _fmt_time(e.get("total_execution_time_seconds", 0)),
            _fmt_cost(e.get("total_cost_usd", 0)),
        ])

    # 按得分率降序排列
    rows.sort(key=lambda r: float(r[3].rstrip("%")) if r[3] != "-" else -1, reverse=True)
    print_table(headers, rows, ["left", "right", "right", "right", "right", "right", "right"])


def compare_by_category(results: List[Dict[str, Any]], filter_cats: Optional[List[str]] = None):
    """按分类对比表。"""
    # 收集所有分类
    all_cats = set()
    for r in results:
        for cat in r.get("summary", {}).get("by_category", {}):
            all_cats.add(cat)
    if filter_cats:
        all_cats = all_cats & set(filter_cats)
    all_cats = sorted(all_cats)

    if not all_cats:
        return

    print("\n📋 分类对比")
    print("=" * 60)

    models = [_short_model(r.get("model", "?")) for r in results]
    headers = ["分类"] + models
    rows = []
    for cat in all_cats:
        row = [cat]
        for r in results:
            cat_data = r.get("summary", {}).get("by_category", {}).get(cat)
            if cat_data:
                row.append(f"{cat_data['score']:.1f}/{cat_data['max']:.0f} ({cat_data['percentage']:.0f}%)")
            else:
                row.append("-")
        rows.append(row)

    print_table(headers, rows, ["left"] + ["right"] * len(models))


def compare_by_task(results: List[Dict[str, Any]], filter_cats: Optional[List[str]] = None):
    """逐任务对比表。"""
    # 收集所有 task_id
    all_tasks = {}
    for r in results:
        for t in r.get("tasks", []):
            tid = t["task_id"]
            if filter_cats and t.get("category") not in filter_cats:
                continue
            if tid not in all_tasks:
                name = t.get("frontmatter", {}).get("name", tid)
                all_tasks[tid] = name

    if not all_tasks:
        return

    print("\n📝 逐任务对比")
    print("=" * 80)

    models = [_short_model(r.get("model", "?")) for r in results]
    headers = ["任务", "名称"] + [f"{m} 得分" for m in models] + [f"{m} tokens" for m in models]
    rows = []

    for tid in sorted(all_tasks):
        name = all_tasks[tid]
        row = [tid, name]
        # 得分列
        for r in results:
            tmap = build_task_map(r)
            t = tmap.get(tid)
            if t:
                score = t["grading"]["mean"]
                row.append(f"{score:.2f}" if score < 1.0 else "1.0")
            else:
                row.append("-")
        # tokens 列
        for r in results:
            tmap = build_task_map(r)
            t = tmap.get(tid)
            if t:
                row.append(_fmt_tokens(t["usage"].get("total_tokens", 0)))
            else:
                row.append("-")
        rows.append(row)

    aligns = ["left", "left"] + ["right"] * (len(models) * 2)
    print_table(headers, rows, aligns)


def compare_efficiency(results: List[Dict[str, Any]]):
    """效率对比表。"""
    print("\n⚡ 效率对比")
    print("=" * 60)

    headers = ["模型", "tokens/任务", "得分/1K tokens", "得分/$", "请求数/任务"]
    rows = []
    for r in results:
        e = r.get("efficiency", {})
        s = r.get("summary", {})
        n_tasks = s.get("total_tasks", 1)
        total_reqs = e.get("total_requests", 0)

        spt = e.get("score_per_1k_tokens")
        spd = e.get("score_per_dollar")

        rows.append([
            _short_model(r.get("model", "?")),
            _fmt_tokens(int(e.get("tokens_per_task", 0))),
            f"{spt:.4f}" if spt else "-",
            f"{spd:.1f}" if spd else "-",
            f"{total_reqs / n_tasks:.1f}" if n_tasks else "-",
        ])

    rows.sort(key=lambda r: float(r[2]) if r[2] != "-" else 0, reverse=True)
    print_table(headers, rows, ["left", "right", "right", "right", "right"])


def generate_markdown(results: List[Dict[str, Any]], filter_cats: Optional[List[str]] = None) -> str:
    """生成 Markdown 格式的对比报告。"""
    lines = ["# SegwayBench 模型对比报告\n"]

    # 总分表
    lines.append("## 总分对比\n")
    models = [_short_model(r.get("model", "?")) for r in results]
    lines.append("| 模型 | 任务数 | 总分 | 得分率 | Tokens | 耗时 | 费用 |")
    lines.append("|------|--------|------|--------|--------|------|------|")
    sorted_results = sorted(results,
        key=lambda r: r.get("summary", {}).get("score_percentage", 0), reverse=True)
    for r in sorted_results:
        s = r.get("summary", {})
        e = r.get("efficiency", {})
        lines.append(
            f"| {_short_model(r.get('model', '?'))} "
            f"| {s.get('total_tasks', 0)} "
            f"| {s.get('total_score', 0):.1f}/{s.get('max_score', 0):.0f} "
            f"| {_fmt_pct(s.get('score_percentage'))} "
            f"| {_fmt_tokens(e.get('total_tokens', 0))} "
            f"| {_fmt_time(e.get('total_execution_time_seconds', 0))} "
            f"| {_fmt_cost(e.get('total_cost_usd', 0))} |"
        )

    # 分类表
    all_cats = set()
    for r in results:
        for cat in r.get("summary", {}).get("by_category", {}):
            all_cats.add(cat)
    if filter_cats:
        all_cats = all_cats & set(filter_cats)
    all_cats = sorted(all_cats)

    if all_cats:
        lines.append("\n## 分类对比\n")
        header = "| 分类 | " + " | ".join(models) + " |"
        sep = "|------|" + "|".join(["------"] * len(models)) + "|"
        lines.append(header)
        lines.append(sep)
        for cat in all_cats:
            row = f"| {cat} "
            for r in results:
                cd = r.get("summary", {}).get("by_category", {}).get(cat)
                if cd:
                    row += f"| {cd['percentage']:.0f}% "
                else:
                    row += "| - "
            row += "|"
            lines.append(row)

    # 逐任务表
    all_tasks = {}
    for r in results:
        for t in r.get("tasks", []):
            tid = t["task_id"]
            if filter_cats and t.get("category") not in filter_cats:
                continue
            if tid not in all_tasks:
                all_tasks[tid] = t.get("frontmatter", {}).get("name", tid)

    if all_tasks:
        lines.append("\n## 逐任务对比\n")
        header = "| 任务 | " + " | ".join(models) + " |"
        sep = "|------|" + "|".join(["------"] * len(models)) + "|"
        lines.append(header)
        lines.append(sep)
        for tid in sorted(all_tasks):
            row = f"| {all_tasks[tid]} "
            for r in results:
                tmap = build_task_map(r)
                t = tmap.get(tid)
                if t:
                    score = t["grading"]["mean"]
                    emoji = "✅" if score >= 1.0 else "⚠️" if score > 0 else "❌"
                    row += f"| {emoji} {score:.0%} "
                else:
                    row += "| - "
            row += "|"
            lines.append(row)

    # 效率表
    lines.append("\n## 效率对比\n")
    lines.append("| 模型 | tokens/任务 | 得分/1K tokens | 请求数/任务 |")
    lines.append("|------|-------------|----------------|-------------|")
    for r in results:
        e = r.get("efficiency", {})
        s = r.get("summary", {})
        n = s.get("total_tasks", 1)
        spt = e.get("score_per_1k_tokens")
        total_reqs = e.get("total_requests", 0)
        lines.append(
            f"| {_short_model(r.get('model', '?'))} "
            f"| {_fmt_tokens(int(e.get('tokens_per_task', 0)))} "
            f"| {f'{spt:.4f}' if spt else '-'} "
            f"| {total_reqs / n:.1f} |" if n else "| - |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SegwayBench 跨模型对比报告")
    parser.add_argument(
        "files", nargs="*",
        help="结果 JSON 文件路径（默认读取 results/merged_*.json）",
    )
    parser.add_argument(
        "--results-dir", default="results",
        help="结果目录（默认 results/）",
    )
    parser.add_argument(
        "--markdown", "-m", metavar="FILE",
        help="输出 Markdown 报告到指定文件",
    )
    parser.add_argument(
        "--category", "-c",
        help="只对比指定分类（逗号分隔）",
    )
    args = parser.parse_args()

    filter_cats = [c.strip() for c in args.category.split(",")] if args.category else None

    # 确定输入文件
    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        results_dir = Path(args.results_dir)
        if not results_dir.exists():
            # 尝试相对于脚本目录
            results_dir = Path(__file__).parent / args.results_dir
        paths = sorted(results_dir.glob("merged_*.json"))

    if not paths:
        print("❌ 未找到结果文件。请指定文件路径或确保 results/ 下有 merged_*.json", file=sys.stderr)
        sys.exit(1)

    results = load_results(paths)
    if len(results) < 1:
        print("❌ 没有可用的结果数据", file=sys.stderr)
        sys.exit(1)

    if len(results) == 1:
        print(f"ℹ️  只有 1 个模型的数据，将显示单模型报告")

    # 终端输出
    compare_overall(results)
    compare_by_category(results, filter_cats)
    compare_by_task(results, filter_cats)
    compare_efficiency(results)

    # Markdown 输出
    if args.markdown:
        md = generate_markdown(results, filter_cats)
        Path(args.markdown).write_text(md, encoding="utf-8")
        print(f"\n📄 Markdown 报告已保存到 {args.markdown}")


if __name__ == "__main__":
    main()
