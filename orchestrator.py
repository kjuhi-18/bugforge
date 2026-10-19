from typing import TypedDict
from langgraph.graph import StateGraph,END
from models.schemas import SharedState,to_dict
from services.llm_service import OllamaService
from agents.planner_agent import PlannerAgent
from agents.bug_analysis_agent import BugAnalysisAgent
from agents.test_generation_agent import TestGenerationAgent
from agents.test_execution_agent import TestExecutionAgent
from agents.code_repair_agent import CodeRepairAgent
from agents.critic_agent import CriticAgent
class GraphState(TypedDict,total=False):
    shared:SharedState
    execution_enabled:bool
    revision_go:bool
class Orchestrator:
    def __init__(self,max_revisions=1,llm_service=None):
        self.max_revisions=max(0,min(int(max_revisions),2)); self.llm=llm_service or OllamaService()
        self.planner=PlannerAgent(); self.analyst=BugAnalysisAgent(); self.generator=TestGenerationAgent()
        self.executor=TestExecutionAgent(); self.repairer=CodeRepairAgent(); self.critic=CriticAgent()
        g=StateGraph(GraphState)
        for n,f in [("planner",self._planner),("analysis",self._analysis),("generation",self._generation),("original_execution",self._original_execution),("repair",self._repair),("repaired_execution",self._repaired_execution),("critic",self._critic),("gate",self._gate)]: g.add_node(n,f)
        g.set_entry_point("planner")
        for a,b in [("planner","analysis"),("analysis","generation"),("generation","original_execution"),("original_execution","repair"),("repair","repaired_execution"),("repaired_execution","critic"),("critic","gate")]: g.add_edge(a,b)
        g.add_conditional_edges("gate",self._next,{"repair":"repair","finish":END}); self.graph=g.compile()
    def run(self,bug_report,source_code,requirements="",use_ollama=False,model=None,execution_enabled=False):
        if not source_code.strip(): raise ValueError("Source code is required.")
        if not requirements.strip(): raise ValueError("Expected behavior is required.")
        if len(source_code)>100000: raise ValueError("Source code exceeds 100 KB.")
        s=SharedState(bug_report.strip(),source_code,requirements,use_ollama,model or self.llm.model); s.logs.append("Workflow initialized.")
        s=self.graph.invoke({"shared":s,"execution_enabled":execution_enabled})["shared"]
        s.final_report={"title":"Multi-Agent Code Repair Report","mode":"Ollama-assisted" if use_ollama else "Rule-based fallback","bug_report":s.bug_report,"requirements":s.requirements,"plan":to_dict(s.plan),"analysis":to_dict(s.analysis),"generation":to_dict(s.generation),"original_execution":to_dict(s.original_execution),"repair":to_dict(s.repair),"repaired_execution":to_dict(s.repaired_execution),"critic":to_dict(s.critic),"revision_count":s.revision_count,"revision_history":s.revision_history,"errors":s.errors,"logs":s.logs}
        return s
    def _planner(self,x):
        s=x["shared"]; s.plan=self.planner.run(s,self.llm); s.logs.append("Planner completed."); return {"shared":s}
    def _analysis(self,x):
        s=x["shared"]; s.analysis=self.analyst.run(s,self.llm); s.logs.append("Bug analysis completed."); return {"shared":s}
    def _generation(self,x):
        s=x["shared"]; s.generation=self.generator.run(s,self.llm); s.logs.append("Test generation completed."); return {"shared":s}
    def _original_execution(self,x):
        s=x["shared"]; s.original_execution=self.executor.run(s,enabled=x.get("execution_enabled",False)); s.logs.append("Original-code test execution completed."); return {"shared":s}
    def _repair(self,x):
        s=x["shared"]; s.repair=self.repairer.run(s,self.llm); s.logs.append("Code repair completed."); return {"shared":s}
    def _repaired_execution(self,x):
        s=x["shared"]
        if s.repair and s.repair.syntax_valid: s.repaired_execution=self.executor.run(s,source=s.repair.repaired_code,enabled=x.get("execution_enabled",False))
        else:
            from models.schemas import TestExecutionOutput
            s.repaired_execution=TestExecutionOutput(False,[],note="Skipped: candidate syntax invalid.")
        s.logs.append("Corrected-code test execution completed."); return {"shared":s}
    def _critic(self,x):
        s=x["shared"]; s.critic=self.critic.run(s,self.llm); s.revision_history.append({"revision":s.revision_count,"verdict":s.critic.verdict,"issues":s.critic.issues,"coverage_gaps":s.critic.coverage_gaps}); s.logs.append("Critic completed."); return {"shared":s}
    def _gate(self,x):
        s=x["shared"]; go=bool(s.critic and s.critic.verdict=="revise" and s.revision_count<self.max_revisions)
        if go: s.revision_count+=1; s.logs.append(f"Bounded repair revision {s.revision_count}/{self.max_revisions}.")
        return {"shared":s,"revision_go":go}
    def _next(self,x): return "repair" if x.get("revision_go",False) else "finish"
