# ISA Reference Model

`scripts/isa_reference.py` is a sequential golden model for the simplified PipeSense educational ISA. It executes the same six benchmark programs at the architectural level and writes:

- `results/reference_model.csv`
- `results/benchmark_disassembly.txt`

## What it checks

- benchmark instruction encodings are coherent
- branch targets terminate
- architectural state changes are deterministic
- every benchmark retires useful instructions
- final register and memory state can be inspected through checksums, summaries, and the HDL-comparable `arch_hash`

`scripts/check_benchmark_parity.py` also parses `tb/benchmark_programs.sv` and checks that the Python reference model uses the same encoded instructions and initial data.

## What it does not check

- pipeline timing
- forwarding correctness
- stall/flush behavior
- adaptive mode switching
- reconfiguration safety
- memory wait timing

Those require HDL simulation and, eventually, formal or synthesis evidence. The reference model is meant to catch benchmark/ISA mistakes before debugging the pipeline.

## How to run

```bash
python scripts/isa_reference.py
```

The artifact checker also runs the reference model in a temporary directory:

```bash
python scripts/check_artifact.py
```

Run the parity check directly with:

```bash
python scripts/check_benchmark_parity.py
```

After HDL simulation, compare retired counts and final architectural data-state hashes against the reference model:

```bash
python scripts/compare_reference.py
```
