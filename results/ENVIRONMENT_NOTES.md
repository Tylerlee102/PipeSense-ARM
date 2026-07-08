# Environment Notes

- Host shell: Windows PowerShell in `C:\Users\tyboy\OneDrive\Documents\mit_2026`.
- Host PATH check: `iverilog`, `vvp`, and `yosys` were not available on the Windows host PATH.
- Fallback used: repo Dockerfile, built as Docker image `pipesense-arm-results`.
- Container toolchain: Icarus Verilog 12.0, VVP 12.0, Yosys 0.33.
- Result generation is being run in the Docker container with this repo mounted at `/workspace`, so output CSVs/logs are written back into the local `results/`, `build/`, and `output/` trees.
- Existing ignored outputs were present before this run even though the task description said those directories were empty; canonical result files are regenerated/overwritten during this workflow rather than treated as fresh evidence.
