import os
import json
import requests
from dotenv import load_dotenv

# Try loading from .env
load_dotenv()

class Signature:
    pass

class InputField:
    def __init__(self, desc=""):
        self.desc = desc

class OutputField:
    def __init__(self, desc=""):
        self.desc = desc

class Module:
    def __init__(self):
        pass
    def load(self, path):
        pass
    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

class Prediction:
    def __init__(self, data):
        self.prerequisites = data.get("prerequisites", "1. AWS Account\n2. LocalStack\n3. CDK CLI")
        self.use_case = data.get("use_case", "Generated Use Case")
        self.core_instructions = data.get("core_instructions", "")
        self.troubleshooting = data.get("troubleshooting", "Check logs.")

class ChainOfThought:
    def __init__(self, signature):
        self.signature = signature

    def __call__(self, **kwargs):
        intent = kwargs.get('intent', 'Dummy Use Case')
        aws_strict_context = kwargs.get('aws_strict_context', '')
        # Truncate to 15,000 chars to avoid OpenAI TPM (Tokens Per Minute) 429 limits on Tier 0
        if len(aws_strict_context) > 15000:
            aws_strict_context = aws_strict_context[:15000] + "... [TRUNCATED]"
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            system_prompt = f"""You are an Expert AWS CDK (v2) Software Engineer specializing in Python.
The user will provide an infrastructure intent. You must respond IN JSON FORMAT ONLY.
The expected JSON keys are:
- "prerequisites": string (Markdown list of prerequisites)
- "use_case": string (A professional summary of what is being built)
- "core_instructions": string (The exact Python AWS CDK v2 code. You MUST provide ONLY the exact code file contents. Define a Stack subclass named EXACTLY `CdkTestingGroundStack`. Define the required AWS components here. DO NOT wrap with ```python at the boundaries of the string, but DO ensure it is valid Python with no syntactical errors, spacing cleanly.)
- `Troubleshoot common issues` directly as detailed sections.

The generated code must strictly pass PEP8 standard flake8 compilation.

You must only output the precise format JSON payload schema. Do not deviate.

Strict Context / Best Practices:
{aws_strict_context}
"""
            # Inject dynamic meta-learned constraints from optimization loop
            learned_rules = ""
            try:
                if os.path.exists("learned_constraints.txt"):
                    with open("learned_constraints.txt", "r", encoding="utf-8") as f:
                        rules = f.read().strip()
                    if rules:
                        learned_rules = "\n\nCRITICAL ENFORCED RULES FROM META-ANALYZER:\n" + rules + "\nYOU MUST FOLLOW THESE RULES OR THE BUILD WILL FAIL."
            except Exception:
                pass
                
            system_prompt += learned_rules

            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                global _dspy_lm_active
                temp_val = _dspy_lm_active.temperature if _dspy_lm_active else 0.5
                payload = {
                    "model": "gpt-4o-mini",
                    "temperature": temp_val,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Intent: {intent}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 2048
                }
                
                resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content']
                data = json.loads(content)
                return Prediction(data)
            except Exception as e:
                print(f"OpenAI Direct API Error: {e}")
                
        # Fallback to pure mock if disconnected
        class FallbackMock:
            prerequisites = "1. AWS Account\n2. LocalStack\n3. CDK CLI"
            use_case = intent
            core_instructions = f"from aws_cdk import Stack\nfrom constructs import Construct\n\n\nclass CdkTestingGroundStack(Stack):\n    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:\n        super().__init__(scope, construct_id, **kwargs)\n        pass\n"
            troubleshooting = "Check keys."
        return FallbackMock()

class Example:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def with_inputs(self, *args):
        return self

_dspy_lm_active = None
def configure(**kwargs):
    global _dspy_lm_active
    if 'lm' in kwargs:
        _dspy_lm_active = kwargs['lm']

class LM:
    def __init__(self, model, api_base="", api_key="", temperature=0.5, **kwargs):
        self.temperature = temperature
