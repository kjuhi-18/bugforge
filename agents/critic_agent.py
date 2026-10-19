from models.schemas import CriticOutput
class CriticAgent:
    name="Critic / Validation Agent"
    def run(self,s,llm=None):
        issues=[]; gaps=[]
        if not s.repair or not s.repair.syntax_valid: issues.append("No syntax-valid repaired candidate.")
        if s.repair and s.repair.repaired_code==s.source_code: issues.append("Repair stage did not change the source.")
        if not s.generation or not s.generation.syntax_valid: issues.append("Generated tests are invalid.")
        elif len(s.generation.tests)<2: gaps.append("Fewer than two tests; edge coverage may be insufficient.")
        if s.generation and any("smoke test" in n.lower() for n in s.generation.notes): gaps.append("Fallback tests are smoke tests, not specification-complete assertions.")
        if not s.original_execution or not s.original_execution.enabled: gaps.append("Original tests not executed; baseline is unverified.")
        if not s.repaired_execution or not s.repaired_execution.enabled: gaps.append("Corrected code tests not executed; candidate is unverified.")
        elif s.repaired_execution.failed or s.repaired_execution.errors: issues.append(f"Corrected code has {s.repaired_execution.failed} failing and {s.repaired_execution.errors} errored tests.")
        if s.repaired_execution and s.repaired_execution.enabled and s.repaired_execution.passed and not s.repaired_execution.failed and not s.repaired_execution.errors:
            gaps.append("Passing finite tests do not prove universal correctness.")
        verdict="revise" if issues else ("warning" if gaps else "approve")
        if llm and s.use_ollama:
            try:
                x=llm.generate_json("Critically validate repaired code. Never approve automatically; finite tests cannot prove all correctness.",f"Requirements: {s.requirements}\nChanges: {s.repair.changes if s.repair else []}\nOriginal execution: {s.original_execution}\nRepaired execution: {s.repaired_execution}\nIssues: {issues}\nGaps: {gaps}",'{"verdict":"warning","issues":[],"coverage_gaps":[],"revision_request":"","summary":"..."}')
                issues += [str(v) for v in x.get("issues",[]) if str(v) not in issues]; gaps += [str(v) for v in x.get("coverage_gaps",[]) if str(v) not in gaps]
                verdict=x.get("verdict","warning")
                if verdict not in ("approve","revise","warning") or (verdict=="approve" and (issues or gaps)): verdict="warning"
                return CriticOutput(verdict,issues,gaps,x.get("revision_request",""),x.get("summary","Validation completed."))
            except Exception as e: s.logs.append("Critic LLM fallback: "+str(e))
        return CriticOutput(verdict,issues,gaps,"Repair remaining failures and retest." if verdict=="revise" else "","Candidate passed available checks." if verdict=="approve" else "Validation incomplete or issues found; do not claim bug-free.")
