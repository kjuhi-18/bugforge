import ast
import re

from models.schemas import TestGenerationOutput, GeneratedTest


class TestGenerationAgent:
    name = "Test Generation Agent"

    def run(self, s, llm=None):
        code = ""
        tests = []
        notes = []

        if llm and s.use_ollama:
            try:
                result = llm.generate_json(
                    (
                        "Generate executable pytest tests for the Python module "
                        "named submitted_module. Return test_code containing at "
                        "least one def test_... function with meaningful assert "
                        "statements. Import the target function from "
                        "submitted_module. Test the stated requirements, including "
                        "boundary cases. Do not use network, shell, subprocess, "
                        "eval, exec, or destructive file operations."
                    ),
                    (
                        f"Expected behavior:\n{s.requirements}\n"
                        f"Bug report:\n{s.bug_report}\n"
                        f"Source code:\n{s.source_code}\n"
                        f"Findings: {[(f.id, f.title) for f in (s.analysis.findings if s.analysis else [])]}"
                    ),
                    (
                        '{"test_code":"imported function and executable pytest '
                        'test functions with assert statements",'
                        '"tests":[{"name":"test_name","description":"what it checks",'
                        '"linked_findings":["F1"]}]}'
                    ),
                )

                candidate = result.get("test_code", "")
                candidate_tests = result.get("tests", [])

                if self._is_executable_test_code(candidate):
                    code = candidate
                    tests = [
                        GeneratedTest(
                            item.get("name", "Generated test"),
                            item.get("description", ""),
                            item.get("linked_findings", []),
                        )
                        for item in candidate_tests
                        if isinstance(item, dict)
                    ]
                else:
                    notes.append(
                        "Ollama returned no executable pytest assertions; "
                        "rule-based fallback used."
                    )

            except Exception as exc:
                notes.append(
                    "LLM generation failed; rule-based fallback used: "
                    + str(exc)
                )

        if not code:
            try:
                tree = ast.parse(s.source_code)
            except SyntaxError as exc:
                return TestGenerationOutput(
                    "", [], False, notes, [str(exc)]
                )

            functions = [
                node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not node.name.startswith("_")
            ]

            requirement_text = (
                (s.requirements or "") + " " + (s.bug_report or "")
            ).lower()

            if (
                "calculate_discount" in s.source_code
                and any(
                    word in requirement_text
                    for word in ("discount", "1000", "threshold")
                )
            ):
                code = (
                    "from submitted_module import calculate_discount\n\n"
                    "def test_below_threshold():\n"
                    "    assert calculate_discount(999) == 999\n\n"
                    "def test_exact_threshold():\n"
                    "    assert calculate_discount(1000) == 900\n\n"
                    "def test_above_threshold():\n"
                    "    assert calculate_discount(1500) == 1350\n"
                )
                tests = [
                    GeneratedTest(
                        "test_below_threshold",
                        "Returns the original price below the threshold.",
                        ["F1"],
                    ),
                    GeneratedTest(
                        "test_exact_threshold",
                        "Applies a 10% discount at exactly 1000.",
                        ["F1"],
                    ),
                    GeneratedTest(
                        "test_above_threshold",
                        "Applies a 10% discount above the threshold.",
                        ["F1"],
                    ),
                ]
                notes.append(
                    "Rule-based discount boundary tests selected from "
                    "the source and requirements."
                )

            elif functions:
                function = functions[0]
                args = [
                    arg.arg
                    for arg in function.args.args
                    if arg.arg not in ("self", "cls")
                ]
                sample_args = ", ".join("0" for _ in args)
                code = (
                    f"from submitted_module import {function.name}\n\n"
                    f"def test_{function.name}_basic_call():\n"
                    f"    result = {function.name}({sample_args})\n"
                    "    assert result is not NotImplemented\n"
                )
                tests = [
                    GeneratedTest(
                        f"test_{function.name}_basic_call",
                        "Smoke test only; does not verify the full specification.",
                    )
                ]
                notes.append(
                    "Generic fallback is a smoke test only. "
                    "Review and add requirement-specific assertions."
                )

            else:
                code = "def test_source_parses():\n    assert True\n"
                tests = [
                    GeneratedTest(
                        "test_source_parses",
                        "Smoke test only; does not validate program behavior.",
                    )
                ]
                notes.append(
                    "No public function found; only a smoke test is possible."
                )

        try:
            ast.parse(code)
        except SyntaxError as exc:
            return TestGenerationOutput(
                code, tests, False, notes + [str(exc)], [str(exc)]
            )

        if not self._is_executable_test_code(code):
            message = "Generated code must contain a test function and assertions."
            return TestGenerationOutput(
                code, tests, False, notes + [message], [message]
            )

        return TestGenerationOutput(code, tests, True, notes, [])

    @staticmethod
    def _is_executable_test_code(code):
        if not isinstance(code, str) or not code.strip():
            return False

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        has_test_function = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        )

        has_assertion = any(
            isinstance(node, ast.Assert) for node in ast.walk(tree)
        )

        return has_test_function and has_assertion
