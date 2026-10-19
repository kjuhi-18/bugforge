from models.schemas import PlanOutput,PlanTask
class PlannerAgent:
    name="Planner Agent"
    def run(self,s,llm=None):
        if llm and s.use_ollama:
            try:
                x=llm.generate_json("Plan specification-driven debugging.",f"Expected behavior:\n{s.requirements}\nOptional bug report:\n{s.bug_report}\nCode:\n{s.source_code[:8000]}",'{"summary":"...","tasks":[{"agent":"...","task":"...","priority":"high","expected_output":"..."}],"execution_order":["..."]}')
                return PlanOutput(x["summary"],[PlanTask(t["agent"],t["task"],t.get("priority","medium"),t["expected_output"]) for t in x["tasks"]],x.get("execution_order",[]))
            except Exception as e: s.logs.append("Planner fallback: "+str(e))
        tasks=[PlanTask("Bug Analysis Agent","Compare source with requirements","high","Candidate discrepancies"),PlanTask("Test Generation Agent","Generate requirement-based tests","high","Syntax-valid pytest"),PlanTask("Test Execution Agent","Run tests against original source","medium","Actual outcomes"),PlanTask("Code Repair Agent","Repair supported defects","high","Corrected candidate"),PlanTask("Critic Agent","Validate corrected candidate","high","Verdict and coverage gaps")]
        return PlanOutput("Compare implementation against the expected behavior, test the discrepancies, repair code and validate the candidate.",tasks,[t.agent for t in tasks])
