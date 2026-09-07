# Benchmark Results

No production-scale benchmark numbers are recorded yet. Benchmark results must contain measured values only.

The repository includes deterministic tools:

```text
python tools/generate_synthetic_data.py benchmark-data/1m.csv --rows 1000000
python tools/benchmark.py benchmark-data/1m.csv --output benchmark-result-1m.json
```

Required progressive targets are 1M, 10M, 50M, 100M and 260M rows. A 260M capability claim must not be made until that run is executed on suitable hardware and recorded.

The build may become feature-complete before the 260M run, but not production-ready solely on that basis.
