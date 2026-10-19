# Multi-Agent Bug Analysis, Test Generation & Code Repair

This project accepts **Python source code and expected behavior**. A known bug report is optional. The agents compare the implementation to the specification, generate tests, execute them when enabled, create corrected code, and validate the candidate.

## Agents
1. Planner — decomposes requirements into analysis, test, repair and validation tasks.
2. Bug Analysis — AST checks and optional LLM hypotheses compare implementation with requirements.
3. Test Generation — creates pytest tests from requirements; syntax-validates test source.
4. Test Execution — runs tests against original code and repaired candidate.
5. Code Repair — generates a full replacement module using Ollama or a narrow deterministic threshold repair.
6. Critic / Validation — reviews test evidence and repair quality, identifies gaps, and may request a bounded revision.

LangGraph coordinates the stages with shared dataclass state and a capped revision loop.

## Windows PowerShell setup
```powershell
cd multi_agent_bug_analyzer
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## Ollama integration (local LLM)
1. Install Ollama for Windows from https://ollama.com/download/windows and make sure it is running.
2. In PowerShell, download and test the coding model:
```powershell
ollama --version
ollama pull qwen2.5-coder:7b
ollama list
ollama run qwen2.5-coder:7b
```
Type a small Python coding request; use `/bye` to exit the interactive session.
3. In a second PowerShell window, activate this project's virtual environment and launch the app:
```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="qwen2.5-coder:7b"
streamlit run app.py
```
4. In the Streamlit sidebar, confirm **Ollama connected** and **Ready**. Choose any installed model from the model dropdown, keep **Use Ollama for analysis and repair** checked, enter the source code and expected behavior, and run the workflow. Test execution is separately opt-in.

The app talks to Ollama's local HTTP API at `/api/tags` and `/api/chat`; no cloud API key is required. The planner, bug-analysis, test-generation, code-repair, and critic agents can use the selected model. If Ollama is unavailable or the model is missing, install/start it and refresh the page. If you want to continue without a model, uncheck Ollama and use the clearly labeled rule-based fallback. The fallback is deliberately limited and is not equivalent to LLM-powered repair.

## Launch
```powershell
streamlit run app.py
```
Open the URL printed by Streamlit, usually http://localhost:8501. Expected behavior is required; known bug report is optional. Download corrected source as `corrected_code.py`.

## Tests
```powershell
python -m pytest tests -q
python -m pytest examples/test_buggy_discount.py -q
```
The example regression suite is expected to fail one test at the exact threshold: the implementation uses `>` while the specification requires `>=`.

## Safety and limitations
Execution is disabled by default and requires explicit acknowledgement. A temporary subprocess and timeout are best-effort containment, **not a secure sandbox**; Python may access host resources with the current user's permissions. Only execute trusted code. Keep execution disabled for untrusted source or deploy a properly configured OS/container sandbox.

AST checks are limited. The rule-based repair only handles a narrow explicit inclusive-threshold case. General repairs require Ollama; generic fallback tests may be smoke tests. Passing finite tests does not prove arbitrary code is universally bug-free. The UI marks candidates unverified if tests are not executed or validation remains incomplete. Review code diffs before using repaired code.

## Architecture summary
A specification-driven LangGraph workflow coordinates planning, static/LLM analysis, test generation, baseline execution, repair, repaired-code execution, and skeptical validation. The shared state stores requirements, findings, tests, both execution results, repair changes, revision history, logs, and report.
