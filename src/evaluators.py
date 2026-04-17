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

from src.student import call_student_llms

logger = logging.getLogger(__name__)

VENV_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "Scripts")


def _score_single_yaml(yaml_content: str) -> tuple[float, str, str]:
    """
    Score a single piece of generated AWS SAM YAML code.
    Returns (score, rule_id, error_trace).
    """
    if not yaml_content or len(yaml_content.strip()) < 10:
        return 0.0, "EMPTY", "YAML was empty or too short."
        
    score = 0.0
    
    # Strip markdown block formatting
    if "```yaml" in yaml_content:
        yaml_content = yaml_content.split("```yaml")[1].split("```")[0]
    elif "```" in yaml_content:
        yaml_content = yaml_content.split("```")[1].split("```")[0]
    
    # Stage 1: Structural Parsing
    try:
        yaml.safe_load(yaml_content)
        score += 0.20
    except yaml.YAMLError as exc:
        logger.debug("Stage 1 FAIL: yaml.safe_load failed")
        line = "unknown"
        if hasattr(exc, 'problem_mark') and exc.problem_mark is not None:
            line = exc.problem_mark.line + 1
        error_trace = f"[YAML Parsing Error] Line {line}: {exc}"
        return 0.0, "YAML_PARSE_ERROR", error_trace
        
    with tempfile.TemporaryDirectory() as temp_dir:
        template_file = os.path.join(temp_dir, "template.yaml")
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
            
        # Stage 2: Specification Validation (cfn-lint)
        cfn_lint_bin = os.path.join(VENV_SCRIPTS, "cfn-lint.exe") if os.name == 'nt' else "cfn-lint"
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
                        first_err = errors[0]
                        rule_id = first_err.get("Rule", {}).get("Id", "E0000")
                        msg = first_err.get("Message", "Unknown error")
                        line = first_err.get("Location", {}).get("Start", {}).get("LineNumber", "Unknown")
                        return score, rule_id, f"[cfn-lint failure] Rule {rule_id} at line {line}: {msg}"
                except json.JSONDecodeError:
                    return score, "CFN_LINT_CRASH", f"cfn-lint output parsing failed: {result.stdout}"
            score += 0.40
        except FileNotFoundError:
            logger.error("cfn-lint binary not found! Please run pip install cfn-lint")
            return score, "SYS_ERR", "cfn-lint execution failed."
            
        # Stage 3: Policy & Security Compliance (cfn-guard)
        cfn_guard_bin = os.path.join(VENV_SCRIPTS, "cfn-guard.exe") if os.name == 'nt' else "cfn-guard"
        rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "aws-hipaa-conformance-pack.guard")
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
                            rule_obj = out_json["not_compliant"][0]
                            rule_name = rule_obj.get("Rule", {}).get("Name", "UNKNOWN_GUARD_RULE")
                            msg = f"[cfn-guard violation] Rule {rule_name} breached HIPAA/security checks."
                            return score, rule_name, msg
                except json.JSONDecodeError:
                    return score, "CFN_GUARD_CRASH", f"cfn-guard error: {result.stderr or result.stdout}"
                    
            score += 0.40
        except FileNotFoundError:
            logger.error("cfn-guard binary not found! Please install it.")
            return score, "SYS_ERR", "cfn-guard execution failed."
            
    return score, "PASS", "YAML template is robust and passed all checks."


def evaluate_prompt_with_details(prompt_text: str, intent_text: str = None) -> tuple[float, list]:
    import concurrent.futures
    from src.student import retry_llm_code
    from src.factory import get_vectorized_feedback
    
    if not prompt_text:
        return 0.0, []
        
    student_results = call_student_llms(prompt_text)
    scores = []
    details = []
    
    def _evaluate_single(result):
        if result["error"] is not None:
            return {"model": result["model"], "score": 0.0, "error": f"API Error: {result['error']}"}
            
        current_code = result["code"]
        best_score = 0.0
        final_error_trace = ""
        
        for attempt in range(3):
            score, rule_id, error_trace = _score_single_yaml(current_code)
            
            penalty = attempt * 0.10
            effective_score = max(0.0, score - penalty)
            best_score = max(best_score, effective_score)
            final_error_trace = error_trace
            
            if score >= 1.0:
                logger.info("Model %s scored %.2f (Base: %.2f, Penalty: %.2f) on attempt %d", result["model"], effective_score, score, penalty, attempt + 1)
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
        return {"model": result["model"], "score": best_score, "error": final_error_trace}
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        computed_details = list(executor.map(_evaluate_single, student_results))
        
    for detail in computed_details:
        scores.append(detail["score"])
        details.append(detail)
        
    avg_score = sum(scores) / len(scores) if scores else 0.0
    logger.info("Metric result: %.3f (avg of %d models)", avg_score, len(scores))
    return avg_score, details

def sam_compile_metric(example, prediction, trace=None):
    prompt_text = getattr(prediction, 'prompt', '')
    intent_text = getattr(example, 'architecture_intent', '')
    avg_score, _ = evaluate_prompt_with_details(prompt_text, intent_text=intent_text)
    
    if trace is not None:
        return avg_score >= 1.0
        
    return avg_score
