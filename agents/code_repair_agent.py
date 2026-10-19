import ast
from models.schemas import RepairOutput
class CodeRepairAgent:
    name="Code Repair Agent"
    def run(self,s,llm=None):
        original=s.source_code
        if s.analysis and s.analysis.errors:
            return RepairOutput(original,[],"none",False,0,["Original source syntax is invalid."],s.analysis.errors)
        if llm and s.use_ollama:
            try:
                x=llm.generate_json("Repair this Python module to meet expected behavior. Return complete source in repaired_code. Preserve APIs and unrelated behavior. No shell/network/filesystem/eval/exec. If ambiguous, explain uncertainty.",f"Expected behavior:\n{s.requirements}\nOptional bug report:\n{s.bug_report}\nOriginal code:\n{s.source_code}\nFindings: {[(f.title,f.evidence,f.recommendation) for f in (s.analysis.findings if s.analysis else [])]}\nOriginal test outcomes: {[(o.nodeid,o.outcome) for o in (s.original_execution.outcomes if s.original_execution else [])]}",'{"repaired_code":"complete source string","changes":["..."],"confidence":0.7,"unresolved":[]}')
                candidate=str(x["repaired_code"]); ast.parse(candidate)
                return RepairOutput(candidate,x.get("changes",["LLM replacement; inspect diff"]), "ollama",True,max(0,min(1,float(x.get("confidence",.55)))),x.get("unresolved",[]),[])
            except Exception as e: s.logs.append("LLM repair failed; trying conservative patch: "+str(e))
        expected=(s.requirements+" "+s.bug_report).lower()
        if any(w in expected for w in ("greater than or equal","at least",">= 1000","inclusive threshold","price >= 1000")):
            lines=original.splitlines()
            for i,line in enumerate(lines):
                if "if" in line and ">" in line and "1000" in line and ">=" not in line:
                    lines[i]=line.replace(">=",">=",1) if ">=" in line else line.replace(">",">=",1)
                    candidate="\n".join(lines)+("\n" if original.endswith("\n") else "")
                    try:
                        ast.parse(candidate)
                        return RepairOutput(candidate,[f"Changed line {i+1} to use an inclusive comparison to match requirements."],"deterministic_rule",True,.82,[],[])
                    except SyntaxError: break
        return RepairOutput(original,[],"no_safe_automatic_patch",True,.1,["No safe deterministic patch supported; candidate remains unverified. Use Ollama or review manually."],[])
