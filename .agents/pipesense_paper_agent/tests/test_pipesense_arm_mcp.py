#!/usr/bin/env python3
"""Light tests for the PipeSense paper agent helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SERVER = ROOT / ".agents" / "pipesense_paper_agent" / "src" / "pipesense_arm_mcp.py"


def load_server():
    spec = importlib.util.spec_from_file_location("pipesense_arm_mcp", SERVER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_has_workflows():
    module = load_server()
    manifest = module.paper_agent_manifest()
    assert "artifact_check" in manifest["workflows"]
    assert manifest["paper2agent_mapping"]["tools"]


def test_summary_identifies_claim_boundaries():
    module = load_server()
    summary = module.summarize_pipesense_paper()
    assert "ARM-like" in " ".join(summary["claim_boundaries"])
    assert summary["available_evidence"]["paper_source"]


def test_search_project_finds_adaptive_language():
    module = load_server()
    result = module.search_project("adaptive", max_matches=5)
    assert result["ok"]
    assert result["matches"]


def test_research_audit_without_running_checks():
    module = load_server()
    audit = module.audit_research_package(run_checks=False, write_report=False)
    assert audit["overall_status"] in {"usable_with_known_limits", "usable_with_mitigated_limits", "needs_attention"}
    assert "result_summary" in audit
    assert "limit_closure" in audit
    assert "findings" in audit


def test_limit_closure_tracks_three_research_limits():
    module = load_server()
    closure = module.assess_research_limit_closure(write_report=False)
    assert closure["overall_status"] in {"actionable_limits_closed_for_current_scope", "limits_need_attention"}
    assert {item["area"] for item in closure["limits"]} == {
        "Workload validity",
        "Hardware realism",
        "Formal coverage",
    }
