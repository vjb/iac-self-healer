"""
Physical Compilation Metric for MIPROv2 (AWS SAM Declarative Validation)

Scores a generated prompt by how well student LLMs can produce
valid AWS SAM YAML code from it. Uses a 3-stage validation pipeline:

  Stage 1: yaml.safe_load      → +0.20 (valid YAML structure)
  Stage 2: cfn-lint            → +0.40 (zero-error definition)
  Stage 3: cfn-guard           → +0.40 (security compliance)
  Penalty: Local auto-heals    → -0.10 (per attempt)
"""
import os
import subprocess
import tempfile
import logging
import yaml
import json
import math
import shutil

from src.student import call_student_llms

logger = logging.getLogger(__name__)

VENV_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "Scripts")


def _score_single_yaml(yaml_content: str, intent_text: str = None) -> tuple[float, str, str]:
    """
    Score a single piece of generated AWS SAM YAML code.
    Returns (score, rule_id, error_trace).
    """
    if not yaml_content or len(yaml_content.strip()) < 10:
        return 0.0, "EMPTY", "YAML was empty or too short."
        
    score = 0.0
    
    import re
    # Strip markdown block formatting robustly
    blocks = re.findall(r"```[a-zA-Z]*\s*(.*?)\s*```", yaml_content, re.DOTALL)
    
    if blocks:
        # Sort blocks by length descending because SAM templates are vastly larger than dummy bash chunks
        blocks.sort(key=len, reverse=True)
        yaml_content = blocks[0].strip()
        # Sort blocks by length descending because SAM templates are vastly larger than dummy bash chunks
    
    # Stage 1: Structural Parsing & Sanitization Middleware
    parsed_obj = None
    try:
        from cfn_flip import to_json
        import json
        # to_json converts native AWS YAML (!Ref, !Sub) safely into standard AWS JSON structure natively
        json_str = to_json(yaml_content)
        parsed_obj = json.loads(json_str)
    except Exception as e:
        # JSON fallback if it drops directly out of structural loops (or if LLM natively outputs JSON)
        try:
            import json
            parsed_obj = json.loads(yaml_content)
        except Exception as fallback_e:
            cfn_error = f"{type(e).__name__}: {e}"
            json_error = f"{type(fallback_e).__name__}: {fallback_e}"
            logger.debug("Stage 1 FAIL: cfn_flip parsing failed, testing JSON fallback...")
            return 0.0, "YAML_PARSE_ERROR", f"CFN_ParseError: {cfn_error} | JSON_ParseError: {json_error}"
            
    if isinstance(parsed_obj, dict):
        if "AWSTemplateFormatVersion" not in parsed_obj:
            parsed_obj["AWSTemplateFormatVersion"] = "2010-09-09"
        if "Transform" not in parsed_obj:
            parsed_obj["Transform"] = "AWS::Serverless-2016-10-31"
        try:
            yaml_content = yaml.dump(parsed_obj, sort_keys=False)
        except Exception as e:
            return 0.0, "YAML_DUMP_ERROR", f"Failed to serialize sanitized template: {e}"
            
    score += 0.20
        
    ram_dir = "R:\\" if os.path.exists("R:\\") else None
    with tempfile.TemporaryDirectory(dir=ram_dir) as temp_dir:
        template_file = os.path.join(temp_dir, "template.yaml")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
            
        # Stage 1.5: Specification Validation (SAM CLI)
        sam_bin = "sam.cmd" if os.name == 'nt' else "sam"
        if os.name == 'nt' and not shutil.which("sam.cmd"):
            sam_bin = r"C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd"
        try:
            sam_result = subprocess.run(
                [sam_bin, "validate", "--lint", "--template-file", template_file],
                capture_output=True, text=True
            )
            if sam_result.returncode != 0:
                logger.debug("Stage 1.5 FAIL: sam validate failed")
                # Apply continuous decay to grant partial credit for surviving native YAML parse
                error_output = f"{sam_result.stdout}\n{sam_result.stderr}".strip()
                num_errors = error_output.lower().count("error") or 1
                score += 0.20 * math.exp(-0.5 * num_errors)
                return score, "SAM_VALIDATION_ERROR", f"[SAM Macro Violation]: {error_output}"
            else:
                score += 0.20
        except FileNotFoundError:
            logger.warning("SAM CLI not found on system! Skipping sam validate.")
            
        # Stage 2: Specification Validation (cfn-lint)
        cfn_lint_bin = os.path.join(VENV_SCRIPTS, "cfn-lint.exe") if os.name == 'nt' else os.path.join(VENV_SCRIPTS, "cfn-lint")
        if not os.path.exists(cfn_lint_bin):
            cfn_lint_bin = "cfn-lint"
        try:
            result = subprocess.run(
                [cfn_lint_bin, "--format", "json", template_file],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.debug("Stage 2 FAIL: cfn-lint failed")
                try:
                    errors = json.loads(result.stdout)
                    if errors:
                        num_errors = len(errors)
                        lint_score = 0.30 * math.exp(-0.5 * num_errors)
                        score += lint_score
                        first_err = errors[0]
                        rule_id = first_err.get("Rule", {}).get("Id", "E0000")
                        
                        err_summaries = []
                        for err in errors[:3]:
                            r_id = err.get("Rule", {}).get("Id", "E0000")
                            m = err.get("Message", "Unknown error")
                            l = err.get("Location", {}).get("Start", {}).get("LineNumber", "Unknown")
                            err_summaries.append(f"[{r_id} at line {l}]: {m}")
                            
                        msg = f"[cfn-lint failure] {num_errors} total errors. Top explicit violations:\n" + "\n".join(err_summaries)
                        return score, rule_id, msg
                except json.JSONDecodeError:
                    return score, "CFN_LINT_CRASH", f"cfn-lint output parsing failed: {result.stdout}"
            else:
                score += 0.30
        except FileNotFoundError:
            logger.error("cfn-lint binary not found! Please run pip install cfn-lint")
            return score, "SYS_ERR", "cfn-lint execution failed."
            
        # Stage 3: Policy & Security Compliance (cfn-guard)
        cfn_guard_bin = os.path.join(VENV_SCRIPTS, "cfn-guard.exe") if os.name == 'nt' else os.path.join(VENV_SCRIPTS, "cfn-guard")
        if not os.path.exists(cfn_guard_bin):
            cfn_guard_bin = "cfn-guard"
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "aws-wafr-conformance-pack.guard")
        if not os.path.exists(rules_path):
            os.makedirs(os.path.dirname(rules_path), exist_ok=True)
            with open(rules_path, "w") as f:
                f.write("rule S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED { AWS::S3::Bucket BucketEncryption[*] exists }")
                
        try:
            result = subprocess.run(
                [cfn_guard_bin, "validate", "--data", template_file, "--rules", rules_path, "--output-format", "json"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.debug("Stage 3 FAIL: cfn-guard violated")
                try:
                    out_json = json.loads(result.stdout)
                    if "not_compliant" in out_json:
                        if out_json["not_compliant"]:
                            num_violations = len(out_json["not_compliant"])
                            guard_score = 0.30 * math.exp(-0.5 * num_violations)
                            score += guard_score
                            rule_obj = out_json["not_compliant"][0]
                            rule_name = rule_obj.get("Rule", {}).get("Name", "UNKNOWN_GUARD_RULE")
                            
                            # Provide explicit AST path structure natively to the student compiler
                            trace_snippet = json.dumps(rule_obj, separators=(',', ':'))[:300]
                            msg = f"[cfn-guard violation] Rule {rule_name} breached AWS WAFR constraints (Total Violations: {num_violations}). Trace node output: {trace_snippet}"
                            return score, rule_name, msg
                except json.JSONDecodeError:
                    return score, "CFN_GUARD_CRASH", f"cfn-guard error: {result.stdout}\n{result.stderr}"
            else:
                score += 0.30
                
        except FileNotFoundError:
            logger.error("cfn-guard binary not found! Please install it.")
            return score, "SYS_ERR", "cfn-guard execution failed."
            
        # Optional Stage 4: Semantic Intent Validation (LLM-as-a-judge)
        if score >= 1.0 and intent_text:
            try:
                from src.student import _call_openai
                judge_prompt = f"Does the following declarative AWS SAM architecture cleanly satisfy the exact user intent defined below?\n\nUser Intent: {intent_text}\n\nAWS SAM YAML:\n{yaml_content}\n\nIf it perfectly satisfies the intent, output strictly 'YES'. If it misses components or hallucinates properties, output 'NO' followed by a 1-sentence technical reason why (e.g., 'NO: Missing explicit DynamoDB Global Secondary Index mapping')."
                res = _call_openai(judge_prompt, api_key=os.environ.get("OPENAI_API_KEY", ""), model_id="gpt-4o-mini")
                
                if res.strip().upper().startswith("YES"):
                    score += 0.20
                    return score, "PASS", "YAML template is robust, secure, and semantically verified."
                else:
                    reason = res.replace("NO", "", 1).replace(":", "", 1).strip()
                    return score, "SEMANTIC_FAILURE", f"Semantic Configuration Missing. The evaluation judge traced: '{reason}'"
            except Exception as e:
                logger.warning("Semantic validation judge error: %s", e)
            
    return score, "PASS", "YAML template is robust and passed physical verification natively."


def evaluate_prompt_with_details(prompt_text: str, intent_text: str = None) -> tuple[float, list]:
    import concurrent.futures
    from src.student import retry_llm_code
    from src.factory import get_vectorized_feedback
    from src.data_loader import record_compiler_failure
    
    if not prompt_text:
        return 0.0, []
        
    student_results = call_student_llms(prompt_text, intent_text=intent_text)
    scores = []
    details = []
    
    def _evaluate_single(result):
        if result["error"] is not None:
            return {"model": result["model"], "score": 0.0, "error": f"API Error: {result['error']}"}
            
        current_code = result["code"]
        best_score = 0.0
        final_error_trace = ""
        
        for attempt in range(3):
            score, rule_id, error_trace = _score_single_yaml(current_code, intent_text=intent_text)
            
            penalty = attempt * 0.10
            effective_score = max(0.0, score - penalty)
            best_score = max(best_score, effective_score)
            final_error_trace = error_trace
            
            if score >= 1.20:
                logger.info("Model %s scored %.2f (Base: %.2f, Penalty: %.2f) with complete semantic verification on attempt %d", result["model"], effective_score, score, penalty, attempt + 1)
                return {"model": result["model"], "score": effective_score, "error": error_trace}
                
            logger.debug("Model %s failed with %.2f on attempt %d. Error trace captured.", result["model"], score, attempt + 1)
            
            if attempt < 2:
                logger.debug("Triggering ChromaDB Vectorized Feedback for %s...", result["model"])
                try:
                    # Query ChromaDB specifically against the rule_id
                    feedback_doc = get_vectorized_feedback(rule_id)
                    retry_context = (
                        f"Your declarative AWS SAM YAML failed validation.\\n"
                        f"Error:\\n{final_error_trace}\\n\\n"
                        f"ChromaDB Oracle Snippet:\\n{feedback_doc}\\n\\n"
                        f"Rewrite the full YAML to satisfy this specific constraint."
                    )
                    current_code = retry_llm_code(result["model"], prompt_text, current_code, retry_context)
                    logger.debug("Retry generation successful, re-evaluating...")
                except Exception as e:
                    logger.warning("Retry API call failed for %s: %s", result["model"], e)
                    break
                    
        logger.info("Model %s scored %.2f (exhausted)", result["model"], best_score)
        
        # Prevent information waste! Physically embed the exhausted syntax limits into ChromaDB's local oracle 
        if final_error_trace and (best_score < 1.0 or "SEMANTIC_FAILURE" in final_error_trace):
            try:
                record_compiler_failure(intent_text or "General", final_error_trace)
                logger.debug("Successfully recorded persistent compiler hallucination trace mapping into ChromaDB Oracle.")
            except Exception as e:
                logger.warning("Feedback Oracle mapping failed natively: %s", e)
                
        return {"model": result["model"], "score": best_score, "error": final_error_trace}
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        computed_details = list(executor.map(_evaluate_single, student_results))
        
    for detail in computed_details:
        if detail.get("error", "").startswith("API Error:"):
            logger.warning("Excluded %s from average calculation due to API connection failure.", detail["model"])
        else:
            scores.append(detail["score"])
        details.append(detail)
        
    avg_score = sum(scores) / len(scores) if scores else 0.0
    logger.info("Metric result: %.3f (avg of %d resolving models)", avg_score, len(scores))
    
    # Real-Time Asynchronous Telemetry Dump (Physical JSONL Tracker)
    import time
    run_dir = os.environ.get("CURRENT_RUN_DIR")
    if run_dir and os.path.exists(run_dir):
        telemetry = {
            "timestamp": int(time.time()),
            "intent": intent_text,
            "avg_score": avg_score,
            "prompt": prompt_text,
            "model_details": details
        }
        telemetry_path = os.path.join(run_dir, "live_telemetry.jsonl")
        try:
            with open(telemetry_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(telemetry) + "\n")
        except Exception as e:
            logger.debug(f"Live telemetry JSONL write securely bypassed due to stream overlap: {e}")
            
    return avg_score, details

def sam_compile_metric(example, prediction, trace=None):
    prompt_text = getattr(prediction, 'prompt', '')
    intent_text = getattr(example, 'architecture_intent', '')
    avg_score, _ = evaluate_prompt_with_details(prompt_text, intent_text=intent_text)
    
    if trace is not None:
        return avg_score >= 1.0
        
    return avg_score
