# Measured data

## Validation VM host calibration

Source: `data/observed/virtual_environment_2026-09-02.json`.

| Metric | Value |
|---|---:|
| Logical CPUs | 5 |
| Visible memory | 6,236,925,952 bytes |
| NVIDIA GPU visible | false |
| Python bytearray copy median | 11.6715 GB/s |
| SHA-256 median | 1.7080 GB/s |
| Temporary filesystem read median | 2.4187 GB/s |
| Temporary filesystem write median | 4.9643 GB/s |

The benchmark used 64 MiB payloads and five repeats. Python object operations, virtualized storage and page cache behavior affect these values.

## Physical workstation host calibration

Source: `data/observed/host_workstation_local.json`.

| Metric | Value |
|---|---:|
| Host platform | Windows 11 Pro (25H2) x86_64 |
| Logical CPUs | 24 (Intel Core i7-13700F) |
| Visible physical memory | 34,175,893,504 bytes (31.83 GiB) |
| NVIDIA GPU visible | true (Discrete NVIDIA GeForce RTX 4080) |
| Python bytearray copy median | 15.2475 GB/s (Max: 16.4879 GB/s) |
| SHA-256 median | 0.5979 GB/s |
| Temporary filesystem read median | 2.0785 GB/s |
| Temporary filesystem write median | 0.1539 GB/s |

Measured on host workstation using 64 MiB buffers and five repeats.

## Synthetic route-pipeline measurement (Validation VM)

Source: `data/observed/synthetic_trace_pipeline_2026-09-02.json`.

| Metric | Value |
|---|---:|
| Units | 4,096 |
| Layers | 36 |
| Top-k | 4 |
| Events | 147,456 |
| JSONL bytes | 27,227,837 |
| Generation | 3.39 s / 43,497 events/s |
| Analysis | 1.76 s / 83,782 events/s |
| Analysis peak RSS | 164.10 MiB |
| Geometry | valid |
| Holdout selection hit rate | 61.19% |
| Holdout full-row hit rate | 12.13% |

## Synthetic route-pipeline measurement (Physical Workstation)

Source: `data/observed/synthetic_trace_pipeline_windows_workstation.json`.

| Metric | Value |
|---|---:|
| Units | 4,096 |
| Layers | 36 |
| Top-k | 4 |
| Events | 147,456 |
| JSONL bytes | 27,302,217 |
| Generation | 2.05 s / 72,081 events/s |
| Analysis | 9.91 s / 14,873 events/s |
| Analysis peak RSS | 78.12 MiB |
| Geometry | valid |
| Holdout selection hit rate | 70.48% |
| Holdout full-row hit rate | 22.33% |

This route distribution was generated with a fixed seed and a biased categorical distribution. It demonstrates the trace pipeline, not a specific production router.

## CI observations

CI records test and packaging compatibility across Python 3.10, 3.11 and 3.12. Passing CI proves the tested software contract; it does not prove target hardware performance.
