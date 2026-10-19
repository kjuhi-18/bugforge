from services.safe_executor import execute_tests
from models.schemas import TestExecutionOutput
class TestExecutionAgent:
    name="Test Execution Agent"
    def run(self,s,source=None,enabled=False):
        if not s.analysis or s.analysis.errors: return TestExecutionOutput(False,[],note="Skipped: source syntax errors.")
        if not s.generation or not s.generation.syntax_valid: return TestExecutionOutput(False,[],note="Skipped: generated tests invalid.")
        return execute_tests(source if source is not None else s.source_code,s.generation.test_code,enabled)
