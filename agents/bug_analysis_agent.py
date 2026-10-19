from models.schemas import AnalysisOutput,Finding
from services.static_analysis import analyze_source
class BugAnalysisAgent:
    name="Bug Analysis Agent"
    def run(self,s,llm=None):
        raw,funcs,errors=analyze_source(s.source_code,s.requirements,s.bug_report)
        findings=[Finding(f"F{i+1}",x["title"],x["description"],x["severity"],x["confidence"],x["evidence"],x["line_numbers"],"static_finding",x["recommendation"]) for i,x in enumerate(raw)]
        if llm and s.use_ollama and not errors:
            try:
                x=llm.generate_json("Compare Python implementation with expected behavior. Label suggestions as hypotheses and cite evidence.",f"Expected:\n{s.requirements}\nOptional bug report:\n{s.bug_report}\nSource:\n{s.source_code}",'{"summary":"...","hypotheses":[{"title":"...","description":"...","severity":"medium","confidence":0.5,"line_numbers":[],"evidence":[],"recommendation":"..."}]}')
                for h in x.get("hypotheses",[])[:8]: findings.append(Finding(f"H{len(findings)+1}",h["title"],h["description"],h.get("severity","medium"),max(0,min(1,float(h.get("confidence",.5)))),h.get("evidence",[]),h.get("line_numbers",[]),"llm_hypothesis",h.get("recommendation","Validate with tests.")))
            except Exception as e: s.logs.append("Analysis LLM fallback: "+str(e))
        if not findings and not errors: findings=[Finding("F1","No static rule matched","No configured static rule matched; correctness is not established.","info",.3,["AST parsing succeeded."],[],"rule_based_hypothesis","Use specification-based tests.")]
        return AnalysisOutput(findings,"Source syntax invalid; repair/execution blocked." if errors else f"Parsed {len(funcs)} function(s); {len(findings)} candidate finding(s).",funcs,errors)
