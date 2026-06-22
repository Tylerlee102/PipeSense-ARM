# Formal Safety Plan

The safety story should eventually move from simulation monitors to formal properties. The current repository includes `formal/reconfig_safety_properties.sv` as a starting point.

## Properties currently expressed

- `reconfig_done` only occurs when the pipeline is empty and no memory wait is active.
- Fetch remains stopped while reconfiguration is active.
- Current mode stays stable while a reconfiguration is active.
- The latched requested mode remains stable until completion.
- A completed reconfiguration installs the latched requested mode.

## Why this is not enough yet

These properties target the reconfiguration unit boundary. They do not prove full-core correctness, instruction conservation, register-file equivalence, memory ordering, or absence of duplicated writeback across arbitrary programs.

The core-level simulation tags are useful because they catch duplicated or backward-moving retirement in normal simulation. A stronger proof would model instruction tokens across all pipeline registers and prove conservation under stalls, flushes, and reconfiguration.

## Next formal milestones

1. Prove `reconfig_unit` properties in isolation.
2. Add bounded model checks for a small core instance with symbolic instructions.
3. Prove instruction-token conservation for non-flushed instructions.
4. Prove no two retired instructions share the same token.
5. Prove register writeback occurs at most once per retiring token.
6. Add assumptions for memory wait fairness so drain eventually completes.
