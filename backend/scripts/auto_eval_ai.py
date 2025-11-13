import argparse
import json
import statistics
import time
from typing import List, Dict, Any

import httpx


BASE_URL_DEFAULT = "http://localhost:8000/api/v1"


def load_cases(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("评测数据格式错误：应为数组")
    if len(data) < 30:
        raise ValueError(f"评测数据不足：当前{len(data)}条，需≥30条")
    return data


def approx_token_count(text: str) -> int:
    if not text:
        return 0
    # 简单近似：按空白分割计数
    return len((text or "").split())


def run_round(cases: List[Dict[str, Any]], base_url: str, use_rag: bool, timeout: float = 15.0) -> Dict[str, Any]:
    client = httpx.Client(timeout=timeout)
    latencies: List[float] = []
    tokens: List[int] = []
    correct_flags: List[bool] = []
    citation_flags: List[bool] = []
    per_case_results: List[Dict[str, Any]] = []

    for idx, c in enumerate(cases, start=1):
        q = c.get("query") or ""
        expected_table = (c.get("expected_selected_table") or "").strip()
        payload = {
            "query": q,
            "use_rag": bool(use_rag),
            # 允许扩展：context/conversation_id/data_source_id
        }
        t0 = time.perf_counter()
        try:
            r = client.post(f"{base_url}/ai/query", json=payload)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(latency_ms)
            if r.status_code != 200:
                per_case_results.append({
                    "query": q,
                    "status": r.status_code,
                    "error": r.text,
                    "latency_ms": latency_ms,
                    "correct": False,
                })
                correct_flags.append(False)
                tokens.append(0)
                citation_flags.append(False)
                continue
            data = r.json().get("data") or {}
            sql = data.get("generated_sql") or ""
            selected_table = (data.get("selected_table") or "").strip()
            dims = data.get("dimensions") or []
            mets = data.get("metrics") or []
            rag_ctx = data.get("rag_context") or ""
            
            # 正确性：以表选择为主
            is_correct = bool(expected_table) and (selected_table.lower() == expected_table.lower())
            correct_flags.append(is_correct)
            tokens.append(approx_token_count(sql))
            # 引用准确率：启用RAG时统计 rag_context 中是否包含预期表名
            has_citation = bool(use_rag) and bool(rag_ctx) and (expected_table.lower() in rag_ctx.lower())
            citation_flags.append(bool(has_citation))

            per_case_results.append({
                "query": q,
                "expected_table": expected_table,
                "selected_table": selected_table,
                "dimensions": dims,
                "metrics": mets,
                "latency_ms": latency_ms,
                "token_count": tokens[-1],
                "correct": is_correct,
                "rag_citation_hit": has_citation,
            })
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(latency_ms)
            correct_flags.append(False)
            tokens.append(0)
            citation_flags.append(False)
            per_case_results.append({
                "query": q,
                "error": str(e),
                "latency_ms": latency_ms,
                "correct": False,
            })

    accuracy = (sum(1 for f in correct_flags if f) / len(correct_flags)) if correct_flags else 0.0
    avg_latency_ms = statistics.mean(latencies) if latencies else 0.0
    avg_tokens = statistics.mean(tokens) if tokens else 0.0
    citation_accuracy = (sum(1 for c in citation_flags if c) / len(citation_flags)) if citation_flags else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "avg_tokens": round(avg_tokens, 2),
        "citation_accuracy": round(citation_accuracy, 4),
        "details": per_case_results,
    }


def main():
    parser = argparse.ArgumentParser(description="AI SQL生成自动评测脚本")
    parser.add_argument("--cases", default="backend/scripts/eval_cases.json", help="评测数据集路径（JSON数组）")
    parser.add_argument("--base_url", default=BASE_URL_DEFAULT, help="后端API基础URL，如 http://localhost:8000/api/v1")
    parser.add_argument("--price_per_1k_tokens", type=float, default=0.002, help="每1000token成本，用于成本估算")
    parser.add_argument("--output", default="backend/scripts/eval_report.json", help="评测报告输出路径")
    args = parser.parse_args()

    cases = load_cases(args.cases)

    # Round 1：不使用RAG
    round1 = run_round(cases, args.base_url, use_rag=False)
    # Round 2：启用RAG
    round2 = run_round(cases, args.base_url, use_rag=True)

    # 成本估算
    def cost(avg_tokens: float) -> float:
        return round((avg_tokens / 1000.0) * args.price_per_1k_tokens, 6)

    result = {
        "rounds": {
            "r1_no_rag": {
                **round1,
                "cost_per_query": cost(round1.get("avg_tokens", 0.0)),
            },
            "r2_with_rag": {
                **round2,
                "cost_per_query": cost(round2.get("avg_tokens", 0.0)),
            },
        },
        "comparison": {
            "accuracy_delta": round(round2["accuracy"] - round1["accuracy"], 4),
            "latency_delta_ms": round(round2["avg_latency_ms"] - round1["avg_latency_ms"], 2),
            "avg_tokens_delta": round(round2["avg_tokens"] - round1["avg_tokens"], 2),
            "citation_accuracy_delta": round(round2["citation_accuracy"] - round1["citation_accuracy"], 4),
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 控制台输出示例指标（与图片示例保持一致维度）
    print(json.dumps({
        "accuracy": result["rounds"]["r1_no_rag"]["accuracy"],
        "avg_latency_ms": result["rounds"]["r1_no_rag"]["avg_latency_ms"],
        "avg_tokens": result["rounds"]["r1_no_rag"]["avg_tokens"],
        "cost_per_query": result["rounds"]["r1_no_rag"]["cost_per_query"],
        "citation_accuracy": result["rounds"]["r2_with_rag"]["citation_accuracy"],
    }, ensure_ascii=False))

    print("\n=== 优化对比（RAG启用后） ===")
    print(json.dumps(result["comparison"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()