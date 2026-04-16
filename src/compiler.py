"""
CDK Synth Compiler Wrapper

Injects generated CDK v2 Python code into the testing ground project,
runs `cdk synth`, and returns the compilation result.
"""
import os
import subprocess
import shutil
import json
import logging

logger = logging.getLogger(__name__)

# Paths relative to project root
CDK_PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cdk-testing-ground")
STACK_FILE = os.path.join(CDK_PROJECT_DIR, "cdk_testing_ground", "cdk_testing_ground_stack.py")
CDK_OUT_DIR = os.path.join(CDK_PROJECT_DIR, "cdk.out")
VENV_PYTHON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "Scripts", "python.exe")


def _clean_cdk_output():
    """Remove cdk.out directory to prevent stale lock files."""
    if os.path.exists(CDK_OUT_DIR):
        shutil.rmtree(CDK_OUT_DIR, ignore_errors=True)


def run_cdk_synth(code: str) -> dict:
    """
    Inject code into the CDK testing ground and run `cdk synth`.
    
    Args:
        code: Complete Python CDK v2 source code defining CdkTestingGroundStack.
        
    Returns:
        dict with keys:
            - success (bool): Whether cdk synth returned exit code 0
            - template (dict or None): Parsed CloudFormation JSON template if successful
            - stderr (str): Filtered stderr output (for error analysis)
            - resource_types (list): List of CloudFormation resource types if successful
    """
    _clean_cdk_output()
    
    # Inject the code
    os.makedirs(os.path.dirname(STACK_FILE), exist_ok=True)
    with open(STACK_FILE, "w", encoding="utf-8") as f:
        f.write(code)
    
    # Safely construct cross-platform command execution
    import sys
    import tempfile
    
    cdk_bin = "cdk.cmd" if sys.platform == "win32" else "cdk"
    python_bin = '..\\\\venv\\\\Scripts\\\\python.exe' if sys.platform == 'win32' else '../venv/bin/python'
    synth_cmd = [cdk_bin, "synth", "-a", f"{python_bin} app.py", "--quiet"]
    
    tmp_out = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
    tmp_out_path = tmp_out.name
    tmp_err = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
    tmp_err_path = tmp_err.name
    tmp_out.close()
    tmp_err.close()
    
    proc = None
    try:
        with open(tmp_out_path, "w", encoding="utf-8") as out_f, open(tmp_err_path, "w", encoding="utf-8") as err_f:
            proc = subprocess.Popen(
                synth_cmd,
                cwd=CDK_PROJECT_DIR,
                stdout=out_f,
                stderr=err_f,
                shell=(sys.platform == 'win32')
            )
            proc.communicate(timeout=120)
            
        with open(tmp_err_path, "r", encoding="utf-8") as f:
            stderr_text = f.read()
    except subprocess.TimeoutExpired:
        if proc:
            # Best practice: terminate the exact child process tree without global taskkills
            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception:
                pass
                
        _clean_cdk_output()
        return {
            "success": False,
            "template": None,
            "stderr": "CDK synth timed out after 120 seconds",
            "resource_types": []
        }
    finally:
        try:
            os.unlink(tmp_out_path)
            os.unlink(tmp_err_path)
        except OSError:
            pass
            
    # Modify returncode check below to use the captured stderr_text
    result_stderr = stderr_text if 'stderr_text' in locals() else ""
    
    # Filter stderr noise
    stderr_lines = result_stderr.split("\n") if result_stderr else []
    filtered = []
    for line in stderr_lines:
        if "typeguard.check_type" in line:
            continue
        if "UserWarning:" in line or "warnings.warn(" in line:
            continue
        if len(line.strip()) == 0:
            continue
        filtered.append(line)
    filtered_stderr = "\n".join(filtered[-30:])  # Last 30 meaningful lines
    
    if proc and proc.returncode != 0:
        _clean_cdk_output()
        return {
            "success": False,
            "template": None,
            "stderr": filtered_stderr,
            "resource_types": []
        }
    
    # Parse CloudFormation template
    template = None
    resource_types = []
    template_path = os.path.join(CDK_OUT_DIR, "CdkTestingGroundStack.template.json")
    
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = json.load(f)
            
            resources = template.get("Resources", {})
            resource_types = list(set(
                r.get("Type", "Unknown") for r in resources.values()
            ))
        except Exception as e:
            logger.warning("Failed to parse CloudFormation template: %s", e)
    
    _clean_cdk_output()
    
    return {
        "success": True,
        "template": template,
        "stderr": filtered_stderr,
        "resource_types": resource_types
    }


def count_cfn_resources(template: dict) -> int:
    """Count the number of distinct resource types in a CloudFormation template."""
    if not template:
        return 0
    resources = template.get("Resources", {})
    return len(set(r.get("Type", "") for r in resources.values()))
