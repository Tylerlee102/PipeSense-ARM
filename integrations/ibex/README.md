# PipeSense-Ibex engineering integration

This integration pins and patches the established lowRISC Ibex core. It does
not use the repository's legacy synthetic processor. Exact upstream revisions
and the verified sv2v archive digest are in `lock.json`.

## Runtime mechanisms

The patched core is built with Ibex's real branch-target ALU and prefetch
buffer. Policy 0 selects late conditional-branch resolution and normal
sequential prefetch. Policy 1 selects the existing early branch-target path and
demand-only instruction fetching. Policy 2 observes retired branches in
64-instruction windows and switches between those two physical paths. A switch
holds new fetch requests, waits for the IF/ID, load-store, and writeback state
to drain, changes the mode, and then resumes fetch. The minimum residency is 64
retired instructions; branch-mode entry and retention thresholds are 6 and 3
branch events per window.

These mechanisms change timing and resource use, not architectural state. The
multi-phase workload alternates eight branch-heavy and straight-line phases and
must produce checksum `DE332F10` while causing repeated adaptive transitions.

## Reproduction

Build the pinned environment, prepare clean upstream sources, and run the full
engineering campaign:

```sh
docker build -t pipesense-arm-ibex-v2 .
python3 scripts/prepare_ibex.py --clean
python3 scripts/run_ibex_engineering.py --skip-prepare
docker run --rm -v "$PWD:/workspace" -w /workspace pipesense-arm-ibex-v2 \
  python3 scripts/run_ibex_post_synth.py
docker run --rm -v "$PWD:/workspace" -w /workspace pipesense-arm-ibex-v2 \
  python3 scripts/run_ibex_formal.py
python3 scripts/validate_ibex_evidence.py
```

`run_ibex_engineering.py --quick` is a CI smoke test with 10 CoreMark
iterations, two Embench programs, and one architecture test. It is not the
committed publication evidence.

The simulator configuration is RV32IMC plus Zicsr, fast multiply/divide, a
writeback stage, the branch-target ALU, and a three-cycle instruction-memory
delay. Programs are loaded into the simple-system RAM at `0x00100000` with
`--meminit=ram,<elf>`. Embench uses `-O2 -march=rv32imc_zicsr -mabi=ilp32
-static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles
-ffreestanding`; exact invocations are preserved in the runner and logs.
CoreMark is the pinned Ibex-vendored EEMBC source and runs 2,000 iterations.
The board patch disables floating-point reporting and an unsupported cache CSR;
the benchmark algorithm is unchanged. All 19 pinned Embench programs retain
their upstream self-checks. The 75 architecture-test signatures are compared
byte-for-byte with the pinned Spike reference model.

## Evidence

`results/ibex/benchmark_results.csv` contains all 291 policy/workload rows.
Raw simulator and program logs are under `results/ibex/logs/`; Spike signatures
are under `results/ibex/reference/`. Tool versions, source revisions, placed
resource/timing reports, and the independent reconciliation report are also
under `results/ibex/`. The deterministic fuzz source covers 500 generated seeds
in one self-checking program execution per policy; the per-seed expectations
are in `verif/fuzz_expected.csv`.

## Limitations

The FPGA comparison synthesizes and places the complete Ibex core plus a common
64-bit LFSR interface-driving harness. That harness contributes identical
stimulus/folding logic to both policies and is not a production SoC. Clock gates
are mapped always-on for this FPGA flow. Power is unavailable because the flow
has neither a characterized ECP5 power model nor benchmark switching activity.

Spike executes every self-checking benchmark ELF to completion, but exact
reference-signature comparison applies to the architecture tests. The new
formal proof is a bounded 8-cycle interface-level proof of the controller's
drain, mode visibility, switch protocol, token accounting under an explicit
valid-retirement assumption, and absence of in-flight tokens at a switch.
Architectural no-loss and no-duplicate retirement for the whole Ibex core are
supported by the passing dynamic tests, not by an unbounded whole-core formal
proof. The older
token-conservation and
no-double-commit proofs in this repository target the legacy synthetic model
and must not be presented as Ibex proofs.
