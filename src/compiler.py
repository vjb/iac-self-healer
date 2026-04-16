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


def _kill_orphan_node_processes():
    """Kill orphaned node.exe processes from previous cdk synth runs (Windows only)."""
    try:
        subprocess.run(
            'wmic process where "name=\'node.exe\' and commandline like \'%cdk%\'" call terminate',
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
    except Exception:
        pass


def _clean_cdk_output():
    """Remove cdk.out directory to prevent stale lock files."""
    _kill_orphan_node_processes()
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
    
    # Run cdk synth
    synth_cmd = f'npx cdk synth -a "..\\\\venv\\\\Scripts\\\\python.exe app.py" --quiet'
    
    try:
        result = subprocess.run(
            synth_cmd,
            cwd=CDK_PROJECT_DIR,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
    except subprocess.TimeoutExpired:
        _clean_cdk_output()
        return {
            "success": False,
            "template": None,
            "stderr": "CDK synth timed out after 60 seconds",
            "resource_types": []
        }
    
    # Filter stderr noise
    stderr_lines = result.stderr.split("\n") if result.stderr else []
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
    
    if result.returncode != 0:
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
