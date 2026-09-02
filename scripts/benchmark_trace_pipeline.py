#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc

from lexa_asymcompute.trace import load_trace, temporal_top_n_holdout, validate_geometry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--tokens", type=int, default=4096)
    parser.add_argument("--layers", type=int, default=36)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--experts", type=int, default=64)
    parser.add_argument("--cache-per-layer", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20260902)
    parser.add_argument("--environment", default=None)
    args = parser.parse_args()

    env_name = args.environment or f"{platform.system().lower()}-host-workstation"

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        # 1. Generator measurement
        tracemalloc.start()
        gen_start = time.perf_counter()
        gen_cmd = [
            sys.executable,
            str(Path(__file__).parent / "generate_trace_demo.py"),
            str(tmp_path),
            "--tokens", str(args.tokens),
            "--layers", str(args.layers),
            "--top-k", str(args.top_k),
            "--experts", str(args.experts),
            "--seed", str(args.seed),
        ]
        subprocess.run(gen_cmd, check=True, capture_output=True)
        gen_elapsed = time.perf_counter() - gen_start
        gen_peak_rss = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
        tracemalloc.stop()

        jsonl_bytes = tmp_path.stat().st_size
        total_events = args.tokens * args.layers

        # 2. Analysis measurement
        tracemalloc.start()
        ana_start = time.perf_counter()
        events = load_trace(tmp_path)
        geo = validate_geometry(events, layers=args.layers, top_k=args.top_k, experts_per_layer=args.experts)
        holdout = temporal_top_n_holdout(events, cache_per_layer=args.cache_per_layer)
        ana_elapsed = time.perf_counter() - ana_start
        ana_peak_rss = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
        tracemalloc.stop()

        payload = {
            "schema_version": "1.0",
            "classification": "observed_synthetic_harness",
            "measured": True,
            "environment": env_name,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": {
                "tokens": args.tokens,
                "layers": args.layers,
                "top_k": args.top_k,
                "events": total_events,
                "jsonl_bytes": jsonl_bytes,
                "elapsed_seconds": round(gen_elapsed, 4),
                "events_per_second": round(total_events / gen_elapsed, 2),
                "peak_rss_mib": round(gen_peak_rss, 4),
            },
            "analysis": {
                "elapsed_seconds": round(ana_elapsed, 4),
                "events_per_second": round(total_events / ana_elapsed, 2),
                "input_throughput_mb_s": round((jsonl_bytes / (1024 * 1024)) / ana_elapsed, 4),
                "peak_rss_mib": round(ana_peak_rss, 4),
                "geometry_valid": geo["valid"],
                "cache_per_layer": args.cache_per_layer,
                "calibration_tokens": holdout["calibration_tokens"],
                "evaluation_tokens": holdout["evaluation_tokens"],
                "selection_hit_rate": holdout["selection_hit_rate"],
                "full_row_hit_rate": holdout["full_row_hit_rate"],
            },
            "notes": "The trace is seeded synthetic routing metadata. Timings are real measurements of this implementation on this host workstation, not neural-network inference throughput.",
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
