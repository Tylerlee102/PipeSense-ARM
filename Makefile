PYTHON ?= python

.PHONY: all sim analyze validate plot sweep ablations safety cost synth audit reference compare parity paper-check paper-preview paper-verify check clean

all: sim plot

sim:
	$(PYTHON) scripts/run_sim.py

analyze:
	$(PYTHON) scripts/analyze_results.py results/sim_output.txt

validate:
	$(PYTHON) scripts/validate_results.py

plot:
	$(PYTHON) scripts/plot_results.py

sweep:
	$(PYTHON) scripts/run_sweep.py

ablations:
	$(PYTHON) scripts/run_ablations.py

safety:
	$(PYTHON) verif/fuzz_runner.py --seeds 500

cost:
	$(PYTHON) scripts/estimate_hardware_cost.py

synth:
	$(PYTHON) scripts/synth_area_report.py

reference:
	$(PYTHON) scripts/isa_reference.py

compare:
	$(PYTHON) scripts/compare_reference.py

parity:
	$(PYTHON) scripts/check_benchmark_parity.py

paper-check:
	$(PYTHON) scripts/check_paper.py

paper-preview:
	$(PYTHON) scripts/build_paper_preview.py

paper-verify: paper-preview
	$(PYTHON) scripts/verify_paper_preview.py

audit:
	$(PYTHON) scripts/audit_requirements.py

check:
	$(PYTHON) scripts/check_artifact.py

clean:
	rm -rf build results
