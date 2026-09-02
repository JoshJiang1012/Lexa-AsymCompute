#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import tempfile
import time


def _memory_copy(size: int, repeats: int) -> dict[str, float]:
    source = bytearray(os.urandom(size))
    target = bytearray(size)
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        target[:] = source
        elapsed = time.perf_counter() - start
        samples.append(size / elapsed / 1e9)
    return {"median_gbps": statistics.median(samples), "min_gbps": min(samples), "max_gbps": max(samples)}


def _sha256(size: int, repeats: int) -> dict[str, float]:
    payload = os.urandom(size)
    samples = []
    digest = ""
    for _ in range(repeats):
        start = time.perf_counter()
        digest = hashlib.sha256(payload).hexdigest()
        elapsed = time.perf_counter() - start
        samples.append(size / elapsed / 1e9)
    return {"median_gbps": statistics.median(samples), "digest_prefix": digest[:16]}


def _file_io(size: int, repeats: int, directory: Path) -> dict[str, float]:
    payload = os.urandom(size)
    write_rates, read_rates = [], []
    directory.mkdir(parents=True, exist_ok=True)
    for _ in range(repeats):
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as handle:
            path = Path(handle.name)
            start = time.perf_counter()
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            write_rates.append(size / (time.perf_counter() - start) / 1e9)
        start = time.perf_counter()
        read_back = path.read_bytes()
        read_rates.append(len(read_back) / (time.perf_counter() - start) / 1e9)
        path.unlink(missing_ok=True)
    return {"write_median_gbps": statistics.median(write_rates), "read_median_gbps": statistics.median(read_rates)}


def _get_visible_memory() -> int | None:
    if hasattr(os, "sysconf"):
        try:
            return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
        except (ValueError, OSError, AttributeError):
            pass
    if os.name == "nt":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
        except Exception:
            pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--size-mib", type=int, default=64)
    parser.add_argument("--repeats", type=int, default=5)
    default_io = "/mnt/data" if Path("/mnt/data").is_dir() else tempfile.gettempdir()
    parser.add_argument("--io-directory", default=default_io)
    parser.add_argument("--environment", default=None)
    args = parser.parse_args()
    size = args.size_mib * 1024 * 1024
    memory_bytes = _get_visible_memory()
    nvidia_visible = Path("/proc/driver/nvidia/gpus").exists() or (shutil.which("nvidia-smi") is not None)
    env_name = args.environment or f"{platform.system().lower()}-host-workstation"
    payload = {
        "schema_version": "1.0",
        "classification": "observed_measurement",
        "measured": True,
        "environment": env_name,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpu_count": os.cpu_count(),
            "visible_memory_bytes": memory_bytes,
            "nvidia_gpu_visible": nvidia_visible,
        },
        "parameters": {"size_bytes": size, "repeats": args.repeats},
        "measurements": {
            "python_bytearray_copy": _memory_copy(size, args.repeats),
            "sha256": _sha256(size, args.repeats),
            "filesystem": _file_io(size, max(2, min(args.repeats, 3)), Path(args.io_directory)),
        },
        "notes": "These measurements characterize this host and the Python harness, observing physical memory and local filesystem performance."
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
