import ast
from models.schemas import SharedState
from services.static_analysis import analyze_source
from agents.test_generation_agent import TestGenerationAgent
from agents.code_repair_agent import CodeRepairAgent
SOURCE="def calculate_discount(price):\n    if price > 1000:\n        return price * .9\n    return price\n"
def test_static_analysis_flags_boundary():
    findings,funcs,errors=analyze_source(SOURCE,"discount at least 1000","")
    assert not errors and "calculate_discount" in funcs
    assert any("Boundary" in f["title"] for f in findings)
def test_generated_tests_are_valid():
    s=SharedState("",SOURCE,"Apply discount when price >= 1000")
    s.analysis=type("A",(),{"findings":[],"errors":[]})()
    result=TestGenerationAgent().run(s)
    assert result.syntax_valid and "test_exact_threshold" in result.test_code
    ast.parse(result.test_code)
def test_rule_repair_fixes_inclusive_threshold():
    s=SharedState("",SOURCE,"Apply discount when price >= 1000")
    s.analysis=type("A",(),{"findings":[],"errors":[]})()
    result=CodeRepairAgent().run(s)
    assert result.syntax_valid and "price >= 1000" in result.repaired_code
    assert result.repaired_code != SOURCE
