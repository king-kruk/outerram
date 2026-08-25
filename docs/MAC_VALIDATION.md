# Physical Apple Silicon validation gate

Package/planner/API correctness can be tested away from a Mac. Metal inference, unified-memory behavior and real SSD performance cannot.

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
```

For repeatable performance runs, avoid starting with significant swap/red memory pressure and prefer AC power.

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

## 5. Create the primary qualification artifact

In another terminal:

```bash
outerram qualify \
  --base-url http://127.0.0.1:8080/v1 \
  --checkpoint "$MODEL" \
  --disk-path "$(dirname "$MODEL")" \
  --prompt 'Implement a correct Python LRU cache with a small unittest suite.' \
  --max-tokens 512 \
  --output qualification.json
```

This must prove marker behavior, tool-call round trip, streaming token accounting/TTFT/tok-s, exact checkpoint provenance, selected strategy, runtime pin status and storage measurements.

## 6. Memory observations

During prefill/decode also record Activity Monitor plus:

```bash
memory_pressure
vm_stat
sysctl vm.swapusage
```

## 7. Coding-agent workload

Before advertising a row as coding-agent validated, run:

- code generation with tests;
- a multi-file bug fix;
- tool invocation and result continuation;
- at least 10 conversational/tool turns;
- a repository-sized prompt/context representative of real use.

## Success criteria

A compatibility row may be marked **validated** only if output is coherent, the process does not OOM/crash, memory pressure/swap is not pathologically sustained, tool calling works when advertised, TTFT/tok-s are measured, and exact hardware/model revision/quantization/context/strategy/storage are recorded.

If resident mode causes unacceptable pressure, test a compatible streaming strategy and disclose it explicitly. Do not force `dense-stream` onto MoE or `moe-stream` onto Dense; the compatibility gate rejects those mismatches.
