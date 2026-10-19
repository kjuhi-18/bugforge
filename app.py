
import json
import difflib

import streamlit as st

from orchestrator import Orchestrator
from services.llm_service import OllamaService


st.set_page_config(
    page_title="Multi-Agent Code Repair",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Multi-Agent Bug Analysis, Test Generation & Code Repair")
st.caption(
    "Provide source code and expected behavior. The system discovers "
    "discrepancies, generates tests, proposes repairs, and validates candidates."
)


# ---------------------------------------------------------
# Helpers: handle strings, dictionaries, and missing values
# ---------------------------------------------------------
def display_text(item):
    """Convert an agent output item into readable text."""
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        for key in ("description", "change", "summary", "message", "text"):
            value = item.get(key)
            if value:
                return str(value)

        return json.dumps(item, indent=2, ensure_ascii=False)

    return str(item)


def safe_metric(obj, attribute, default=0):
    """Read a metric safely from an optional execution result."""
    if obj is None:
        return default

    return getattr(obj, attribute, default)


def show_execution(label, execution):
    """Display execution details without assuming every field exists."""
    with st.expander(label + " execution details"):
        if execution is None:
            st.info("No execution result is available.")
            return

        note = getattr(execution, "note", None)
        if note:
            st.write(note)

        stdout = getattr(execution, "stdout", "")
        stderr = getattr(execution, "stderr", "")

        if stdout:
            st.markdown("**Standard output**")
            st.code(stdout)

        if stderr:
            st.markdown("**Errors / standard error**")
            st.code(stderr)

        outcomes = getattr(execution, "outcomes", []) or []

        for outcome in outcomes:
            result = display_text(
                {
                    "outcome": getattr(outcome, "outcome", "unknown"),
                    "test": getattr(outcome, "nodeid", "Unknown test"),
                }
            )
            st.write(result)


# ---------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------
llm = OllamaService()
status = llm.status()

with st.sidebar:
    st.header("Runtime")

    reachable = bool(status.get("reachable", False))
    installed_models = status.get("models", []) or []

    st.write(
        "Ollama:",
        "🟢 Connected" if reachable else "🔴 Not connected",
    )

    if reachable and installed_models:
        preferred = (
            llm.model
            if llm.model in installed_models
            else installed_models[0]
        )

        selected_model = st.selectbox(
            "Ollama model",
            installed_models,
            index=installed_models.index(preferred),
        )
    else:
        selected_model = llm.model
        st.text_input(
            "Configured model",
            value=llm.model,
            disabled=True,
        )

    model_ready = reachable and selected_model in installed_models

    if not reachable:
        st.info(
            "Start Ollama, then refresh this page. "
            "Check using: ollama list"
        )
    elif not installed_models:
        st.warning(
            "Ollama is running, but no models are installed. "
            "Run: ollama pull qwen2.5-coder:7b"
        )
    else:
        st.success(f"Ready · {selected_model}")

    use_llm = st.checkbox(
        "Use Ollama for analysis and repair",
        value=bool(model_ready),
        disabled=not model_ready,
    )

    revisions = st.selectbox(
        "Maximum repair revisions",
        [0, 1, 2],
        index=1,
    )

    st.warning(
        "Code execution is not a secure sandbox. "
        "Only run trusted code."
    )

    execute = st.checkbox(
        "I understand; enable test execution",
        value=False,
    )


# ---------------------------------------------------------
# Inputs
# ---------------------------------------------------------
demo = (
    "def calculate_discount(price):\n"
    "    if price > 1000:  # bug: requirement says >= 1000\n"
    "        return price * 0.90\n"
    "    return price\n"
)

with st.form("inputs"):
    bug = st.text_area(
        "Optional known bug report",
        "",
        placeholder="Optional — you do not need to know the bug.",
    )

    expected = st.text_area(
        "Expected behavior / requirements *",
        "Apply a 10% discount whenever price is greater than "
        "or equal to 1000. Otherwise return the original price.",
    )

    uploaded = st.file_uploader(
        "Upload .py file (optional)",
        type=["py"],
    )

    default_source = (
        uploaded.getvalue().decode("utf-8", errors="replace")
        if uploaded
        else demo
    )

    source = st.text_area(
        "Source code *",
        default_source,
        height=260,
    )

    submit = st.form_submit_button(
        "Analyze, test, repair and validate",
        type="primary",
        use_container_width=True,
    )


# ---------------------------------------------------------
# Run workflow
# ---------------------------------------------------------
if submit:
    if not source.strip():
        st.error("Please provide Python source code.")
    elif not expected.strip():
        st.error("Please provide the expected behavior.")
    else:
        try:
            with st.spinner(
                "Running the multi-agent workflow..."
            ):
                result = Orchestrator(
                    revisions,
                    OllamaService(model=selected_model),
                ).run(
                    bug,
                    source,
                    expected,
                    use_llm,
                    selected_model,
                    execute,
                )

                st.session_state["result"] = result

        except Exception as exc:
            st.error(f"Workflow failed: {exc}")


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------
r = st.session_state.get("result")

if r:
    plan = getattr(r, "plan", None)
    analysis = getattr(r, "analysis", None)
    generation = getattr(r, "generation", None)
    original_execution = getattr(r, "original_execution", None)
    repaired_execution = getattr(r, "repaired_execution", None)
    repair = getattr(r, "repair", None)
    critic = getattr(r, "critic", None)

    stages = [
        ("Planner", plan),
        ("Analysis", analysis),
        ("Test generation", generation),
        ("Original tests", original_execution),
        ("Repair", repair),
        ("Critic", critic),
    ]

    columns = st.columns(6)

    for column, (name, obj) in zip(columns, stages):
        column.metric(
            name,
            "Done" if obj is not None else "Not run",
        )

    final_report = getattr(r, "final_report", {}) or {}
    mode = final_report.get("mode", "Unknown")
    st.caption(f"Mode: {mode}")

    tabs = st.tabs(
        [
            "Corrected code",
            "Tests",
            "Findings & plan",
            "Critic & history",
            "Report",
        ]
    )

    # -----------------------------------------------------
    # Corrected code
    # -----------------------------------------------------
    with tabs[0]:
        candidate = (
            getattr(repair, "repaired_code", "")
            if repair
            else ""
        )

        passed = safe_metric(repaired_execution, "passed")
        failed = safe_metric(repaired_execution, "failed")
        errors = safe_metric(repaired_execution, "errors")
        execution_enabled = safe_metric(
            repaired_execution,
            "enabled",
            False,
        )

        verified = bool(
            repaired_execution is not None
            and execution_enabled
            and passed > 0
            and failed == 0
            and errors == 0
        )

        if verified:
            st.success(
                "All executed generated tests passed against this "
                "candidate. This is not proof of universal correctness."
            )
        else:
            st.warning(
                "Candidate is unverified or has validation issues."
            )

        st.write(
            "Repair method:",
            getattr(repair, "repair_method", "Unavailable")
            if repair
            else "Unavailable",
        )

        confidence = getattr(repair, "confidence", None) if repair else None

        st.write(
            "Confidence:",
            f"{confidence:.0%}"
            if isinstance(confidence, (int, float))
            else "N/A",
        )

        st.markdown("**Changes made**")

        changes = getattr(repair, "changes", []) or [] if repair else []

        if changes:
            for change in changes:
                st.write(f"• {display_text(change)}")
        else:
            st.caption("No change descriptions were provided.")

        unresolved = (
            getattr(repair, "unresolved", []) or []
            if repair
            else []
        )

        for item in unresolved:
            st.warning(display_text(item))

        st.markdown("**Corrected Python code**")
        st.code(candidate or "# No candidate generated", language="python")

        st.download_button(
            "Download corrected_code.py",
            candidate,
            file_name="corrected_code.py",
            mime="text/x-python",
            disabled=not bool(candidate),
        )

        original_code = getattr(r, "source_code", "") or ""

        if candidate and candidate != original_code:
            diff = "".join(
                difflib.unified_diff(
                    original_code.splitlines(True),
                    candidate.splitlines(True),
                    fromfile="original.py",
                    tofile="corrected_code.py",
                )
            )

            with st.expander("View code diff"):
                st.code(diff, language="diff")

    # -----------------------------------------------------
    # Tests and execution
    # -----------------------------------------------------
    with tabs[1]:
        a, b, c = st.columns(3)

        a.metric(
            "Original passed",
            safe_metric(original_execution, "passed"),
        )
        b.metric(
            "Original failed",
            safe_metric(original_execution, "failed"),
        )
        c.metric(
            "Corrected failed",
            safe_metric(repaired_execution, "failed"),
        )

        test_code = (
            getattr(generation, "test_code", "")
            if generation
            else ""
        )

        st.markdown("**Generated test code**")
        st.code(
            test_code or "# No test code generated",
            language="python",
        )

        st.download_button(
            "Download generated tests",
            test_code,
            file_name="test_generated.py",
            mime="text/x-python",
            disabled=not bool(test_code),
        )

        show_execution("Original code", original_execution)
        show_execution("Corrected code", repaired_execution)

    # -----------------------------------------------------
    # Findings and plan
    # -----------------------------------------------------
    with tabs[2]:
        if plan:
            st.subheader("Execution plan")

            for task in getattr(plan, "tasks", []) or []:
                agent = getattr(task, "agent", "Agent")
                task_text = getattr(task, "task", "")
                priority = getattr(task, "priority", "normal")

                st.write(
                    f"**{agent}** — {task_text} ({priority})"
                )

        if analysis:
            st.subheader("Bug analysis")
            st.write(getattr(analysis, "summary", ""))

            findings = getattr(analysis, "findings", []) or []

            for finding in findings:
                finding_id = getattr(finding, "id", "Finding")
                title = getattr(finding, "title", "Untitled")
                severity = getattr(finding, "severity", "unknown")
                confidence = getattr(finding, "confidence", None)

                confidence_text = (
                    f"{confidence:.0%}"
                    if isinstance(confidence, (int, float))
                    else "N/A"
                )

                heading = (
                    f"{finding_id} · {title} · "
                    f"{severity} · {confidence_text}"
                )

                with st.expander(heading):
                    st.write(getattr(finding, "description", ""))
                    st.caption(getattr(finding, "status", ""))

                    for evidence in (
                        getattr(finding, "evidence", []) or []
                    ):
                        st.code(display_text(evidence))

                    st.write(
                        "Lines:",
                        getattr(finding, "line_numbers", []),
                    )
                    st.write(
                        "Recommendation:",
                        getattr(finding, "recommendation", ""),
                    )

    # -----------------------------------------------------
    # Critic and history
    # -----------------------------------------------------
    with tabs[3]:
        if critic:
            verdict = getattr(critic, "verdict", "unknown")

            st.subheader(f"Verdict: {verdict.upper()}")
            st.write(getattr(critic, "summary", ""))

            for issue in getattr(critic, "issues", []) or []:
                st.error(display_text(issue))

            for gap in getattr(critic, "coverage_gaps", []) or []:
                st.warning(display_text(gap))
        else:
            st.info("The Critic agent did not produce a result.")

        st.markdown("**Revision history**")
        st.write(getattr(r, "revision_history", []) or [])

        st.markdown("**Workflow logs**")
        logs = getattr(r, "logs", []) or []

        for log in logs:
            st.write(f"• {display_text(log)}")

    # -----------------------------------------------------
    # Reports
    # -----------------------------------------------------
    with tabs[4]:
        report_json = json.dumps(
            final_report,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        st.download_button(
            "Download JSON report",
            report_json,
            file_name="code_repair_report.json",
            mime="application/json",
        )

        requirements = getattr(r, "requirements", "") or ""
        repaired_code = (
            getattr(repair, "repaired_code", "")
            if repair
            else ""
        )
        critic_summary = (
            getattr(critic, "summary", "No critic summary available.")
            if critic
            else "No critic result available."
        )

        markdown_report = (
            "# Code Repair Report\n\n"
            f"## Requirements\n{requirements}\n\n"
            f"## Mode\n{mode}\n\n"
            "## Corrected code\n"
            "```python\n"
            f"{repaired_code}\n"
            "```\n\n"
            f"## Verdict\n{critic_summary}\n"
        )

        st.download_button(
            "Download Markdown report",
            markdown_report,
            file_name="code_repair_report.md",
            mime="text/markdown",
        )

else:
    st.info(
        "Enter Python code and its expected behavior. "
        "A known bug report is optional."
    )
