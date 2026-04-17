"""
Multi-Model Student LLM Dispatcher

Sends prompts to multiple student LLMs (GPT-4o, Groq) and returns
generated AWS SAM YAML code. Groq errors are handled gracefully.
"""
import os
import logging
import requests
import re

logger = logging.getLogger(__name__)

STUDENT_SYSTEM_PROMPT = """You are an AWS Serverless Application Model (SAM) developer. Given the instructional prompt below, produce a complete, valid declarative AWS SAM YAML template.

MANDATORY RULES:
- Output ONLY valid AWS SAM YAML code. No markdown wrappers, no explanations.
- The template MUST declare `Transform: AWS::Serverless-2016-10-31` at the top level.
- Resources must utilize robust `AWS::Serverless::*` architectures (e.g. `AWS::Serverless::Function`, `AWS::Serverless::Api`).
- Ensure all resources clearly declare strict types, IAM constraints, and required environment mappings.
- For compliance, verify KMS encryptions on buckets and explicit network subnets on Lambda functions.
"""


def _clean_code_output(raw: str) -> str:
    """Strip markdown wrappers and chat text from LLM output."""
    code = raw.strip()
    # Remove markdown code blocks
    if code.startswith("```yaml"):
        code = code[len("```yaml"):].strip()
    if code.startswith("```yml"):
        code = code[len("```yml"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()
    return code


def _call_openai(prompt_text: str, api_key: str, system_prompt: str = STUDENT_SYSTEM_PROMPT, model_id: str = "gpt-4o") -> str:
    """Call OpenAI models to generate AWS SAM YAML from a prompt."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
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


def _call_openrouter(prompt_text: str, api_key: str, model_id: str, system_prompt: str = STUDENT_SYSTEM_PROMPT) -> str:
    """Call OpenRouter to generate AWS SAM YAML from a prompt using a specific model."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
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


def retry_llm_code(model_id: str, original_prompt: str, previous_code: str, error_trace: str) -> str:
    """Send back the compiler failure state to prompt self-correction."""
    api_key = os.environ.get("OPENAI_API_KEY", "") if model_id == "gpt-4o" else os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise Exception("API key missing for retry")
        
    messages = [
        {"role": "system", "content": STUDENT_SYSTEM_PROMPT},
        {"role": "user", "content": original_prompt},
        {"role": "assistant", "content": previous_code},
        {"role": "user", "content": f"The code you generated failed compilation with the following error trace:\n\n{error_trace}\n\nRewrite the full declarative AWS SAM YAML template correctly to resolve this."}
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    url = "https://api.openai.com/v1/chat/completions" if model_id == "gpt-4o" else "https://openrouter.ai/api/v1/chat/completions"
    
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.0
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=300)
    resp.raise_for_status()
    json_resp = resp.json()
    if "error" in json_resp:
        raise Exception(f"API Error during retry: {json_resp['error']}")
    return _clean_code_output(json_resp['choices'][0]['message']['content'])


def call_student_llms(prompt_text: str, intent_text: str = None) -> list:
    """
    Send a prompt to multiple student LLMs and return all successful results concurrently.
    
    Returns:
        list of dicts, each with:
            - model (str): Model name
            - code (str): Generated AWS SAM YAML code
            - error (str or None): Error message if the call failed
    """
    import concurrent.futures
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    
    system_prompt = STUDENT_SYSTEM_PROMPT
    if intent_text:
        try:
            from src.data_loader import get_sam_reference
            rag_context = get_sam_reference(intent_text)
            system_prompt += f"\n\n--- PRE-EMPTIVE ARCHITECTURE RESTRICTIONS & RAG KNOWLEDGE BASE ---\n{rag_context}\n"
            logger.debug("Successfully injected %d bytes of pre-emptive ChromaDB context into system prompt globally.", len(rag_context))
        except Exception as e:
            logger.warning("Failed to inject pre-emptive RAG: %s", e)
    
    results = []
    
    def _fetch_openai():
        if not openai_key: return None
        try:
            code = _call_openai(prompt_text, openai_key, system_prompt=system_prompt)
            logger.info("GPT-4o student: generated %d chars of code", len(code))
            return {"model": "gpt-4o", "code": code, "error": None}
        except Exception as e:
            logger.error("GPT-4o student failed: %s", e)
            return {"model": "gpt-4o", "code": "", "error": str(e)}

    def _fetch_openrouter(model_id):
        if not openrouter_key: return None
        try:
            code = _call_openrouter(prompt_text, openrouter_key, model_id, system_prompt=system_prompt)
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
