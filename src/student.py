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
        headers=headers, json=payload, timeout=300
    )
    resp.raise_for_status()
    return _clean_code_output(resp.json()['choices'][0]['message']['content'])


def _call_openrouter(prompt_text: str, api_key: str, model_id: str) -> str:
    """Call OpenRouter to generate CDK code from a prompt using a specific model."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": STUDENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.0
    }
    
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers, json=payload, timeout=300
    )
    resp.raise_for_status()
    # Check if there is an error physically returned in the JSON payload from OpenRouter
    json_resp = resp.json()
    if "error" in json_resp:
        raise Exception(f"OpenRouter Error: {json_resp['error']}")
    return _clean_code_output(json_resp['choices'][0]['message']['content'])


def call_student_llms(prompt_text: str) -> list:
    """
    Send a prompt to multiple student LLMs and return all successful results concurrently.
    
    Returns:
        list of dicts, each with:
            - model (str): Model name
            - code (str): Generated CDK v2 Python code
            - error (str or None): Error message if the call failed
    """
    import concurrent.futures
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    
    results = []
    
    def _fetch_openai():
        if not openai_key: return None
        try:
            code = _call_openai(prompt_text, openai_key)
            logger.info("GPT-4o student: generated %d chars of code", len(code))
            return {"model": "gpt-4o", "code": code, "error": None}
        except Exception as e:
            logger.error("GPT-4o student failed: %s", e)
            return {"model": "gpt-4o", "code": "", "error": str(e)}

    def _fetch_openrouter(model_id):
        if not openrouter_key: return None
        try:
            code = _call_openrouter(prompt_text, openrouter_key, model_id)
            logger.info("OpenRouter student [%s]: generated %d chars of code", model_id, len(code))
            return {"model": model_id, "code": code, "error": None}
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', None)
            if status in (429, 503):
                logger.warning("OpenRouter rate limited (HTTP %s) for %s.", status, model_id)
            else:
                logger.warning("OpenRouter error for %s: %s", model_id, e)
            return {"model": model_id, "code": "", "error": f"HTTP {status}"}
        except Exception as e:
            logger.warning("OpenRouter student [%s] failed: %s", model_id, e)
            return {"model": model_id, "code": "", "error": str(e)}

    # Parallelize LLM API requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        if openai_key:
            futures.append(executor.submit(_fetch_openai))
            
        if openrouter_key:
            or_models = [
                "anthropic/claude-3.7-sonnet",
                "deepseek/deepseek-chat",
                "meta-llama/llama-3.3-70b-instruct"
            ]
            for m in or_models:
                futures.append(executor.submit(_fetch_openrouter, m))
                
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    return results
