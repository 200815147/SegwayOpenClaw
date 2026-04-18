#!/usr/bin/env python3
"""把 results/ 目录下同一模型的多个单任务结果合并为一个汇总 JSON。

用法:
    python merge_results.py [results_dir]

默认 results_dir = 当前目录下的 results/
输出: results/ 下生成 merged_{model_slug}.json
"""

import json, os, sys, re
from collections import defaultdict
from pathlib import Path


def model_slug(filename: str) -> str:
    """从文件名 '0001_ztf-deepseek-v3-2.json' 提取模型标识 'ztf-deepseek-v3-2'"""
    m = re.match(r"^\d+_(.+)\.json$", filename)
    return m.group(1) if m else ""


def merge(results_dir: str):
    results_dir = Path(results_dir)
    # 按模型分组
    groups: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(results_dir.iterdir()):
        if f.suffix == ".json" and not f.name.startswith("merged_"):
            slug = model_slug(f.name)
            if slug:
                groups[slug].append(f)

    for slug, files in groups.items():
        all_tasks = []
        model_name = ""
        safety_mode = ""
        benchmark_version = ""

        for fp in files:
            data = json.loads(fp.read_text())
            model_name = model_name or data.get("model", "")
            safety_mode = safety_mode or data.get("safety_mode", "")
            benchmark_version = benchmark_version or data.get("benchmark_version", "")
            all_tasks.extend(data.get("tasks", []))

        # 去重: 同一 task_id 保留最新（后出现的覆盖）
        seen = {}
        for t in all_tasks:
            seen[t["task_id"]] = t
        tasks = list(seen.values())

        # --- 重算 summary ---
        total_score = sum(t["grading"]["mean"] for t in tasks)
        max_score = sum(t["grading"]["runs"][0]["max_score"] for t in tasks if t["grading"]["runs"])
        by_cat: dict[str, dict] = defaultdict(lambda: {"tasks": 0, "score": 0.0, "max": 0.0})
        for t in tasks:
            cat = t.get("category", "unknown")
            by_cat[cat]["tasks"] += 1
            by_cat[cat]["score"] += t["grading"]["mean"]
            if t["grading"]["runs"]:
                by_cat[cat]["max"] += t["grading"]["runs"][0]["max_score"]
        for v in by_cat.values():
            v["percentage"] = round(v["score"] / v["max"] * 100, 1) if v["max"] else 0.0

        summary = {
            "total_tasks": len(tasks),
            "total_score": round(total_score, 4),
            "max_score": round(max_score, 4),
            "score_percentage": round(total_score / max_score * 100, 1) if max_score else 0.0,
            "by_category": dict(by_cat),
        }

        # --- 重算 efficiency ---
        total_tokens = sum(t["usage"]["total_tokens"] for t in tasks)
        total_input = sum(t["usage"]["input_tokens"] for t in tasks)
        total_output = sum(t["usage"]["output_tokens"] for t in tasks)
        total_cost = sum(t["usage"]["cost_usd"] for t in tasks)
        total_reqs = sum(t["usage"]["request_count"] for t in tasks)
        total_time = sum(t["execution_time"] for t in tasks)
        n_with_usage = sum(1 for t in tasks if t["usage"]["total_tokens"] > 0)

        per_task = []
        for t in tasks:
            score = t["grading"]["mean"]
            tok = t["usage"]["total_tokens"]
            per_task.append({
                "task_id": t["task_id"],
                "score": score,
                "total_tokens": tok,
                "cost_usd": t["usage"]["cost_usd"],
                "tokens_per_score_point": round(tok / score, 1) if score else None,
            })

        n = len(tasks)
        efficiency = {
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": round(total_cost, 6),
            "total_requests": total_reqs,
            "total_execution_time_seconds": round(total_time, 2),
            "tasks_with_usage_data": n_with_usage,
            "tokens_per_task": round(total_tokens / n, 1) if n else 0,
            "cost_per_task_usd": round(total_cost / n, 6) if n else 0,
            "score_per_1k_tokens": round(total_score / (total_tokens / 1000), 6) if total_tokens else None,
            "score_per_dollar": round(total_score / total_cost, 4) if total_cost else None,
            "per_task": per_task,
        }

        merged = {
            "model": model_name,
            "benchmark_version": benchmark_version,
            "safety_mode": safety_mode,
            "merged_from": [f.name for f in files],
            "tasks": tasks,
            "summary": summary,
            "efficiency": efficiency,
        }

        out = results_dir / f"merged_{slug}.json"
        out.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
        print(f"✅ {slug}: {len(tasks)} tasks → {out.name}")


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "results")
    merge(d)
