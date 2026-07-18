PYTHON ?= python

.PHONY: all sim analyze validate plot sweep ablations evidence evidence-check baseline standard-audit safety formal cost synth post-synth audit reference compare parity check summary-check paper-check paper-build paper-verify paper-ready clean

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

evidence:
	$(PYTHON) scripts/generate_publication_evidence.py

evidence-check:
	$(PYTHON) scripts/validate_publication_evidence.py

baseline:
	$(PYTHON) scripts/run_adaptive_baseline.py --seeds 500

standard-audit:
	$(PYTHON) scripts/audit_standard_benchmarks.py

safety:
	$(PYTHON) verif/fuzz_runner.py --seeds 500

formal:
	$(PYTHON) scripts/run_formal.py

cost:
	$(PYTHON) scripts/estimate_hardware_cost.py

synth:
	$(PYTHON) scripts/synth_area_report.py

post-synth:
	$(PYTHON) scripts/run_post_synth.py

reference:
	$(PYTHON) scripts/isa_reference.py

compare:
	$(PYTHON) scripts/compare_reference.py

parity:
	$(PYTHON) scripts/check_benchmark_parity.py

audit:
	$(PYTHON) scripts/audit_requirements.py

check:
	$(PYTHON) scripts/check_artifact.py

summary-check:
	$(PYTHON) scripts/check_results_summary.py

paper-check:
	$(PYTHON) scripts/check_paper.py

paper-build:
	$(PYTHON) scripts/build_paper_preview.py

paper-verify:
	$(PYTHON) scripts/verify_paper_preview.py

paper-ready:
	$(PYTHON) scripts/check_paper.py
	$(PYTHON) scripts/build_paper_preview.py
	$(PYTHON) scripts/verify_paper_preview.py

clean:
	rm -rf build results
