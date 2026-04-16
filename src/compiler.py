"""
CDK Synth Compiler Wrapper

Injects generated CDK v2 Python code into ephemeral workspaces,
runs `cdk synth`, and returns the compilation result securely in parallel.
"""
import os
import subprocess
import shutil
import json
import logging
import sys
import tempfile

logger = logging.getLogger(__name__)

# Absolute paths for cross-platform resolution and binary referencing
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CDK_SCAFFOLD_DIR = os.path.join(PROJECT_ROOT, "cdk-testing-ground")

# Absolute path to python binary for isolated temp directories
VENV_PYTHON_ABS = os.path.abspath(
    os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe") 
    if sys.platform == 'win32' 
    else os.path.join(PROJECT_ROOT, "venv", "bin", "python")
)

def run_cdk_synth(code: str) -> dict:
    """
    Inject code into an ephemeral workspace and run `cdk synth` in isolation.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Clone scaffold files
        shutil.copy(os.path.join(CDK_SCAFFOLD_DIR, "app.py"), tmp_dir)
        shutil.copy(os.path.join(CDK_SCAFFOLD_DIR, "cdk.json"), tmp_dir)
        
        # Build the exact logical namespace expected by app.py
        module_path = os.path.join(tmp_dir, "cdk_testing_ground")
        os.makedirs(module_path, exist_ok=True)
        
        with open(os.path.join(module_path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
            
        stack_file = os.path.join(module_path, "cdk_testing_ground_stack.py")
        with open(stack_file, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Construct isolated execution parameter mapping
        cdk_bin = "cdk.cmd" if sys.platform == "win32" else "cdk"
        synth_cmd = [cdk_bin, "synth", "-a", f"{VENV_PYTHON_ABS} app.py", "--quiet"]
        
        tmp_out = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
        tmp_err = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
        tmp_out.close()
        tmp_err.close()
        
        proc = None
        try:
            with open(tmp_out.name, "w", encoding="utf-8") as out_f, open(tmp_err.name, "w", encoding="utf-8") as err_f:
                proc = subprocess.Popen(
                    synth_cmd,
                    cwd=tmp_dir,  # Execute natively in the safe transient partition
                    stdout=out_f,
                    stderr=err_f,
                    shell=(sys.platform == 'win32')
                )
                proc.communicate(timeout=120)
                
            with open(tmp_err.name, "r", encoding="utf-8") as f:
                stderr_text = f.read()
        except subprocess.TimeoutExpired:
            if proc:
                try:
                    if sys.platform == "win32":
                        subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        proc.kill()
                except Exception:
                    pass
            return {
                "success": False,
                "template": None,
                "stderr": "CDK synth timed out after 120 seconds",
                "resource_types": []
            }
        finally:
            try:
                os.unlink(tmp_out.name)
                os.unlink(tmp_err.name)
            except OSError:
                pass
                
        # Filter stderr noise
        result_stderr = stderr_text if 'stderr_text' in locals() else ""
        stderr_lines = result_stderr.split("\n") if result_stderr else []
        filtered = []
        for line in stderr_lines:
            if "typeguard.check_type" in line or "UserWarning:" in line or "warnings.warn(" in line:
                continue
            if not line.strip():
                continue
            filtered.append(line)
        filtered_stderr = "\n".join(filtered[-30:])
        
        if proc and proc.returncode != 0:
            return {
                "success": False,
                "template": None,
                "stderr": filtered_stderr,
                "resource_types": []
            }
        
        # Pluck synthesized cloudformation off disk cleanly before tmp directory falls out of scope
        template = None
        resource_types = []
        template_path = os.path.join(tmp_dir, "cdk.out", "CdkTestingGroundStack.template.json")
        
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
