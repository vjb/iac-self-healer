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


def _score_single_code(code: str) -> float:
    """
    Score a single piece of generated CDK code through the 5-stage pipeline.
    Returns a float between 0.0 and 1.0.
    """
    if not code or len(code.strip()) < 10:
        return 0.0
    
    # Stage 1: AST parse (fast-fail)
    if not _parse_ast(code):
        logger.debug("Stage 1 FAIL: ast.parse failed")
        return 0.0
    score = 0.10
    
    # Stage 2: Stack class check (fast-fail)
    if not _has_stack_class(code):
        logger.debug("Stage 2 FAIL: no Stack class found")
        return score
    score += 0.10
    
    # Stage 3: flake8 (non-blocking but scored)
    flake8_errors = _run_flake8(code)
    if flake8_errors == 0:
        score += 0.10
    else:
        logger.debug("Stage 3: %d flake8 errors", flake8_errors)
    
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
        logger.debug("Stage 4 FAIL: cdk synth failed\n%s", synth_result["stderr"][:200])
    
    return score


def cdk_compile_metric(example, prediction, trace=None):
    """
    MIPROv2 metric function.
    
    Takes a DSPy example (with architecture_intent) and a prediction
    (with prompt), feeds the prompt to student LLMs, compiles each
    result, and returns the average score across all successful models.
    
    Args:
        example: DSPy Example with `architecture_intent` field
        prediction: DSPy prediction with `prompt` field
        trace: Optional trace argument (required by MIPROv2 signature)
        
    Returns:
        float: Score between 0.0 and 1.0
    """
    prompt_text = getattr(prediction, 'prompt', '')
    if not prompt_text:
        return 0.0
    
    # Call student LLMs
    student_results = call_student_llms(prompt_text)
    
    # Score each successful student response
    scores = []
    for result in student_results:
        if result["error"] is not None:
            continue  # Skip failed models (graceful degradation)
        code = result["code"]
        score = _score_single_code(code)
        logger.info("Model %s scored %.2f", result["model"], score)
        scores.append(score)
    
    if not scores:
        logger.warning("No student models returned valid responses")
        return 0.0
    
    # Average across successful models
    avg_score = sum(scores) / len(scores)
    logger.info("Metric result: %.3f (avg of %d models)", avg_score, len(scores))
    return avg_score
