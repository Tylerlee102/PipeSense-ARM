# Formal Safety Plan

The safety story should eventually move from simulation monitors to formal properties. The current repository includes `formal/reconfig_safety_properties.sv` for the reconfiguration unit, `formal/token_conservation_properties.sv` for abstract instruction-token conservation, and `verif/sva_safety.sv` as an executable simulation assertion monitor.

## Properties currently expressed

- `reconfig_done` only occurs when the pipeline is empty and no memory wait is active.
- Fetch remains stopped while reconfiguration is active.
- Current mode stays stable while a reconfiguration is active.
- The latched requested mode remains stable until completion.
- A completed reconfiguration installs the latched requested mode.
- Core-level fuzz checks monitor monotonic retirement tags, safe mode commit,
  fetch gating, stable mode during reconfiguration, and bounded stall time.
- `formal/token_conservation.sby` proves an abstract five-stage token model in
  which every fetched token is accounted for as live, retired, or flushed; live
  tags are pairwise unique; and retirement consumes the writeback token.

## Why this is not enough yet

The reconfiguration properties target the reconfiguration unit boundary. The token-conservation properties prove an abstract pipeline-token model, not the full core. Together they still do not prove full-core correctness, register-file equivalence, memory ordering, or absence of duplicated writeback across arbitrary programs.

The core-level simulation tags are useful because they catch duplicated or backward-moving retirement in normal simulation. `docs/safety_proof_sketch.md` states the current invariants and maps them to `verif/sva_safety.sv` and the token-conservation formal job. A stronger proof would bind the token abstraction directly to `arm_like_core` and prove conservation under the core's actual stalls, flushes, and reconfiguration.

## Next formal milestones

1. Prove `reconfig_unit` properties in isolation.
2. Add bounded model checks for a small core instance with symbolic instructions.
3. Bind the token-conservation properties into a reduced `arm_like_core` formal instance.
4. Prove no two retired instructions share the same token in the full core.
5. Prove register writeback occurs at most once per retiring token.
6. Add assumptions for memory wait fairness so drain eventually completes.
