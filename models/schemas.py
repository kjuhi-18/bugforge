from dataclasses import dataclass, field, asdict
from typing import Any
@dataclass
class PlanTask:
    agent:str; task:str; priority:str; expected_output:str
@dataclass
class PlanOutput:
    summary:str; tasks:list[PlanTask]; execution_order:list[str]
@dataclass
class Finding:
    id:str; title:str; description:str; severity:str="medium"; confidence:float=.5
    evidence:list[str]=field(default_factory=list); line_numbers:list[int]=field(default_factory=list)
    status:str="static_finding"; recommendation:str=""
@dataclass
class AnalysisOutput:
    findings:list[Finding]; summary:str; source_functions:list[str]; errors:list[str]=field(default_factory=list)
@dataclass
class GeneratedTest:
    name:str; description:str; linked_findings:list[str]=field(default_factory=list)
@dataclass
class TestGenerationOutput:
    test_code:str; tests:list[GeneratedTest]; syntax_valid:bool; notes:list[str]=field(default_factory=list); errors:list[str]=field(default_factory=list)
@dataclass
class TestOutcome:
    nodeid:str; outcome:str; message:str=""
@dataclass
class TestExecutionOutput:
    enabled:bool; outcomes:list[TestOutcome]; passed:int=0; failed:int=0; errors:int=0
    duration_seconds:float=0; stdout:str=""; stderr:str=""; note:str=""
@dataclass
class RepairOutput:
    repaired_code:str; changes:list[str]; repair_method:str; syntax_valid:bool; confidence:float
    unresolved:list[str]=field(default_factory=list); errors:list[str]=field(default_factory=list)
@dataclass
class CriticOutput:
    verdict:str; issues:list[str]; coverage_gaps:list[str]; revision_request:str=""; summary:str=""
@dataclass
class SharedState:
    bug_report:str; source_code:str; requirements:str=""; use_ollama:bool=False; model:str=""
    plan:PlanOutput|None=None; analysis:AnalysisOutput|None=None; generation:TestGenerationOutput|None=None
    original_execution:TestExecutionOutput|None=None; repair:RepairOutput|None=None
    repaired_execution:TestExecutionOutput|None=None; critic:CriticOutput|None=None
    revision_count:int=0; revision_history:list[dict[str,Any]]=field(default_factory=list)
    errors:list[str]=field(default_factory=list); logs:list[str]=field(default_factory=list); final_report:dict[str,Any]=field(default_factory=dict)
def to_dict(obj):
    if hasattr(obj,"__dataclass_fields__"): return {k:to_dict(v) for k,v in asdict(obj).items()}
    if isinstance(obj,list): return [to_dict(v) for v in obj]
    if isinstance(obj,dict): return {k:to_dict(v) for k,v in obj.items()}
    return obj
