import os, requests, json
class OllamaService:
    def __init__(self,base_url=None,model=None,timeout=None):
        self.base_url=(base_url or os.getenv("OLLAMA_BASE_URL","http://localhost:11434")).rstrip("/")
        self.model=model or os.getenv("OLLAMA_MODEL","qwen2.5-coder:7b")
        self.timeout=int(timeout or os.getenv("OLLAMA_TIMEOUT_SECONDS","45"))
    def status(self):
        try:
            r=requests.get(self.base_url+"/api/tags",timeout=min(5,self.timeout)); r.raise_for_status()
            models=[m.get("name","") for m in r.json().get("models",[])]
            return {"reachable":True,"models":models,"model_available":self.model in models}
        except Exception as e: return {"reachable":False,"models":[],"model_available":False,"error":str(e)}
    def generate_json(self,system,prompt,shape):
        try:
            r=requests.post(self.base_url+"/api/chat",json={"model":self.model,"stream":False,"format":"json",
                "options":{"temperature":.1},"messages":[{"role":"system","content":system+" Return only JSON matching "+shape},
                {"role":"user","content":prompt}]},timeout=self.timeout)
            r.raise_for_status(); obj=json.loads(r.json()["message"]["content"])
            if not isinstance(obj,dict): raise ValueError("Expected JSON object")
            return obj
        except Exception as e: raise RuntimeError("Ollama call failed: "+str(e)) from e
