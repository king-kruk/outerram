# Physical Apple Silicon validation gate

Package, planner and API correctness can be tested away from a Mac. Metal inference, unified-memory behavior, process footprint and real SSD performance cannot.

## 1. Install

```bash
./scripts/install-mac.sh
source .venv/bin/activate
outerram --version
outerram pins --json
```

## 2. Machine baseline

```bash
outerram doctor --json | tee doctor.json
memory_pressure
sysctl vm.swapusage
```

For repeatable performance runs, avoid starting with significant swap or red memory pressure and prefer AC power.

## 3. Materialize and validate the exact checkpoint

```bash
REMOTE=owner/model
MODEL="$(outerram fetch "$REMOTE" --path-only)"
outerram inspect "$MODEL" --json | tee model.json
outerram plan "$MODEL" --json | tee plan.json
outerram check "$MODEL" --json | tee compatibility.json
outerram bootstrap "$MODEL"
outerram ready "$MODEL" --json | tee ready.json
```

For an existing local checkpoint set `MODEL=/path/to/model`. OuterRAM refuses a floating Hub ID at execution time.

## 4. Serve on loopback

```bash
outerram serve "$MODEL" --host 127.0.0.1 --port 8080
```

On macOS rc3+, the validated launcher uses process replacement. The selected runtime should occupy the launcher PID; there must not be a second waiting OuterRAM CLI process solely supervising it.

In another terminal identify the listening runtime and process tree:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
ps -axo pid,ppid,rss,vsz,command | grep -E 'outerram|mlx_lm|mlx-flash|streamlx' | grep -v grep
```

Retain this output with the qualification evidence.

## 5. Create the primary qualification artifact

```bash
outerram qualify \
  --base-url http://127.0.0.1:8080/v1 \
  --checkpoint "$MODEL" \
  --disk-path "$(dirname "$MODEL")" \
  --prompt 'Implement a correct Python LRU cache with a small unittest suite.' \
  --max-tokens 512 \
  --output qualification.json
```

This must prove marker behavior, tool-call round trip, streaming token accounting, exact checkpoint provenance, selected strategy, runtime pin status and storage measurements.

## 6. Memory observations

Measure **system-level** memory during idle-after-load, prefill and decode. Runtime allocator counters are useful but are not accepted as the sole memory measurement.

Record:

```bash
memory_pressure
vm_stat
sysctl vm.swapusage
```

For the runtime PID from `lsof`, also capture:

```bash
ps -o pid,ppid,rss,vsz,%mem,command -p <PID>
footprint <PID>
```

At minimum retain:

- baseline system memory pressure and swap before model load;
- runtime RSS and `footprint` after model load but before a request;
- peak observed runtime/system footprint during prefill;
- peak observed runtime/system footprint during decode;
- swap before and after the workload;
- whether any extra OuterRAM launcher process remains resident;
- selected strategy and resident budget.

Do not infer total unified-memory usage from checkpoint bytes alone. Do not use synthetic matrix values as physical memory measurements.

## 7. A/B the 16 GiB boundary

For a near-fit dense model on a 16 GiB Mac, compare the default plan with the compatible alternative rather than assuming either path is faster:

- automatic/default strategy;
- forced `resident` when compatibility permits it;
- `dense-stream` when compatibility permits it.

Record TTFT, decode throughput, process/system footprint, swap and memory-pressure behavior for each run. A resident path is preferred only if it remains stable and materially faster without pathological pressure; streaming is preferred when the resident path causes unsafe pressure or swap.

## 8. Coding-agent workload

Before advertising a row as workload validated, run:

- code generation with tests;
- a multi-file bug fix;
- tool invocation and result continuation;
- at least 10 conversational or tool turns;
- a repository-sized context representative of real use.

## Success criteria

A compatibility row may be marked **validated** only if output is coherent, the process does not OOM or crash, memory pressure and swap are not pathologically sustained, tool calling works when advertised, TTFT and throughput are measured, and exact hardware, model revision, quantization, context, strategy and storage are recorded.

If resident mode causes unacceptable pressure, test a compatible streaming strategy and disclose it explicitly. Do not force `dense-stream` onto MoE or `moe-stream` onto Dense; the compatibility gate rejects those mismatches.
