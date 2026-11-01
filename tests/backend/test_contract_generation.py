from scripts.generate_contracts import ROOT, artifacts


def test_frontend_contract_includes_complete_rule_catalog() -> None:
    content = artifacts()[ROOT / "frontend/src/api/generated.ts"]
    assert "export type RuleCatalog = {" in content
    assert "rules: Array<RuleDefinition>;" in content
    assert "extra_version: string | null;" in content
    assert "patterns: Array<RulePattern>;" in content
    assert 'confidence: "documented" | "needs-review";' in content
