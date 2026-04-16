"""
Physical Compilation Metric for MIPROv2

Scores a generated prompt by how well student LLMs can produce
valid CDK v2 code from it. Uses a 5-stage fast-fail pipeline:

  Stage 1: ast.parse()      → +0.10 (valid Python syntax)
  Stage 2: Stack class       → +0.10 (contains Stack inheritance)
  Stage 3: flake8             → +0.10 (no critical lint errors)
  Stage 4: cdk synth          → +0.50 (CloudFormation generated)
  Stage 5: Resource richness  → +0.20 (3+ distinct resource types)
"""
import ast
import os
import subprocess
import tempfile
import logging

from src.compiler import run_cdk_synth, count_cfn_resources
from src.student import call_student_llms

logger = logging.getLogger(__name__)

VENV_PYTHON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "Scripts", "python.exe")


def _parse_ast(code: str) -> bool:
    """Check if code is valid Python syntax."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _has_stack_class(code: str) -> bool:
    """Check if code defines a class that inherits from Stack."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name == "Stack":
                        return True
        return False
    except Exception:
        return False


def _run_flake8(code: str) -> int:
    """Run flake8 on code and return the number of critical errors."""
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(code)
            tmp_path = f.name
        
        result = subprocess.run(
            [VENV_PYTHON, "-m", "flake8", "--select=E9,F63,F7,F82", tmp_path],
            capture_output=True, text=True, timeout=15
        )
        
        os.unlink(tmp_path)
        
        if result.stdout.strip():
            return len([l for l in result.stdout.strip().split('\n') if l.strip()])
        return 0
    except Exception as e:
        logger.warning("flake8 check failed: %s", e)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return 0  # Don't penalize if flake8 itself fails


def _score_single_code(code: str) -> tuple[float, str]:
    """
    Score a single piece of generated CDK code through the 5-stage pipeline.
    Returns a tuple of (score, error_trace).
    """
    if not code or len(code.strip()) < 10:
        return 0.0, "Code was empty or too short."
    
    # Stage 1: AST parse (fast-fail)
    if not _parse_ast(code):
        logger.debug("Stage 1 FAIL: ast.parse failed")
        return 0.0, "Stage 1 FAIL: Invalid Python syntax (ast.parse failed)."
    score = 0.10
    
    # Stage 2: Stack class check (fast-fail)
    if not _has_stack_class(code):
        logger.debug("Stage 2 FAIL: no Stack class found")
        return score, "Stage 2 FAIL: No class definition inherently inheriting from 'Stack' found."
    score += 0.10
    
    # Stage 3: flake8 (non-blocking but scored)
    flake8_errors = _run_flake8(code)
    curr_error_trace = ""
    if flake8_errors == 0:
        score += 0.10
    else:
        logger.debug("Stage 3: %d flake8 errors", flake8_errors)
        curr_error_trace += f"Stage 3 WARNING: {flake8_errors} critical flake8 lint errors detected.\\n"
    
    # Stage 4: cdk synth (the big one — 50% of score)
    synth_result = run_cdk_synth(code)
    if synth_result["success"]:
        score += 0.50
        logger.debug("Stage 4 PASS: cdk synth succeeded")
        
        # Stage 5: Resource richness
        resource_count = count_cfn_resources(synth_result["template"])
        if resource_count >= 3:
            score += 0.20
        elif resource_count >= 1:
            score += 0.10
        logger.debug("Stage 5: %d resource types found", resource_count)
    else:
        logger.debug("Stage 4 FAIL: cdk synth failed\\n%s", synth_result["stderr"][:200])
        curr_error_trace += f"Stage 4 FAIL: cdk synth failed! Traceback:\\n{synth_result['stderr']}\\n"
    
    return score, curr_error_trace.strip()


def evaluate_prompt_with_details(prompt_text: str) -> tuple[float, list]:
    """
    Executes student LLM inference and runs the evaluation logic.
    Returns (avg_score, list_of_model_details).
    """
    import concurrent.futures
    if not prompt_text:
        return 0.0, []
        
    student_results = call_student_llms(prompt_text)
    scores = []
    details = []
    
    def _evaluate_single(result):
        if result["error"] is not None:
            return {"model": result["model"], "score": 0.0, "error": f"API Error: {result['error']}"}
            
        score, error_trace = _score_single_code(result["code"])
        logger.info("Model %s scored %.2f", result["model"], score)
        return {"model": result["model"], "score": score, "error": error_trace}
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        computed_details = list(executor.map(_evaluate_single, student_results))
        
    for detail in computed_details:
        scores.append(detail["score"])
        details.append(detail)
        
    if not scores:
        logger.warning("No student models returned valid responses")
        return 0.0, details
        
    avg_score = sum(scores) / len(scores)
    logger.info("Metric result: %.3f (avg of %d models)", avg_score, len(scores))
    return avg_score, details


def cdk_compile_metric(example, prediction, trace=None):
    """
    MIPROv2 metric function.
    
    Takes a DSPy example (with architecture_intent) and a prediction
    (with prompt), feeds the prompt to student LLMs, compiles each
    result, and returns the average score across all successful models.
    """
    prompt_text = getattr(prediction, 'prompt', '')
    avg_score, _ = evaluate_prompt_with_details(prompt_text)
    
    if trace is not None:
        # STRICT DSPY BOOTSTRAP GATING:
        # If DSPy is evaluating this specific trace to determine if it should be added 
        # to the prompt as a permanent few-shot example, we MUST return a boolean.
        # Only perfectly compiled architectures (score >= 0.70) are adopted!
        return avg_score >= 0.70
        
    return avg_score
