"""
Multi-Model Student LLM Dispatcher

Sends prompts to multiple student LLMs (GPT-4o, Groq) and returns
generated CDK v2 code. Groq errors are handled gracefully.
"""
import os
import logging
import requests
import re

logger = logging.getLogger(__name__)

STUDENT_SYSTEM_PROMPT = """You are an AWS CDK v2 Python developer. Given the instructional prompt below, produce a complete, valid AWS CDK v2 Python stack.

MANDATORY RULES:
- Output ONLY valid Python AWS CDK v2 code. No markdown wrappers, no explanations.
- The class must be named CdkTestingGroundStack and inherit from Stack.
- Use only `aws_cdk` imports (CDK v2). NEVER use `aws_cdk.core` (that is CDK v1).
- Import Construct from the `constructs` package: `from constructs import Construct`
- Import RemovalPolicy from aws_cdk directly: `from aws_cdk import RemovalPolicy`
- Use SubnetType.PRIVATE_WITH_EGRESS, not PRIVATE_WITH_NAT or PRIVATE.
- Use DynamoDB Attribute objects: `dynamodb.Attribute(name='id', type=dynamodb.AttributeType.STRING)`
- For ELBv2 targets, import from aws_elasticloadbalancingv2_targets, not aws_elasticloadbalancingv2.
"""


def _clean_code_output(raw: str) -> str:
    """Strip markdown wrappers and chat text from LLM output."""
    code = raw.strip()
    # Remove markdown code blocks
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code


def _call_openai(prompt_text: str, api_key: str) -> str:
    """Call GPT-4o to generate CDK code from a prompt."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": STUDENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.0
    }
    
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers, json=payload, timeout=90
    )
    resp.raise_for_status()
    return _clean_code_output(resp.json()['choices'][0]['message']['content'])


def _call_groq(prompt_text: str, api_key: str) -> str:
    """Call Groq to generate CDK code from a prompt. Free tier — may fail."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": STUDENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.0
    }
    
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=90
    )
    resp.raise_for_status()
    return _clean_code_output(resp.json()['choices'][0]['message']['content'])


def call_student_llms(prompt_text: str) -> list:
    """
    Send a prompt to multiple student LLMs and return all successful results.
    
    Returns:
        list of dicts, each with:
            - model (str): Model name
            - code (str): Generated CDK v2 Python code
            - error (str or None): Error message if the call failed
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    
    results = []
    
    # GPT-4o (primary — must succeed)
    if openai_key:
        try:
            code = _call_openai(prompt_text, openai_key)
            results.append({"model": "gpt-4o", "code": code, "error": None})
            logger.info("GPT-4o student: generated %d chars of code", len(code))
        except Exception as e:
            logger.error("GPT-4o student failed: %s", e)
            results.append({"model": "gpt-4o", "code": "", "error": str(e)})
    
    # Groq (secondary — graceful degradation)
    if groq_key:
        try:
            code = _call_groq(prompt_text, groq_key)
            results.append({"model": "groq-llama-3.3-70b", "code": code, "error": None})
            logger.info("Groq student: generated %d chars of code", len(code))
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', None)
            if status in (429, 503):
                logger.warning("Groq rate limited (HTTP %s). Skipping gracefully.", status)
            else:
                logger.warning("Groq HTTP error: %s. Skipping gracefully.", e)
            results.append({"model": "groq-llama-3.3-70b", "code": "", "error": f"HTTP {status}"})
        except Exception as e:
            logger.warning("Groq student failed: %s. Skipping gracefully.", e)
            results.append({"model": "groq-llama-3.3-70b", "code": "", "error": str(e)})
    
    return results
