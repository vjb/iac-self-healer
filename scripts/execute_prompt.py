import os
import subprocess
import re

def main():
    print(">>> 1. Generating Prompt...")
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    
    subprocess.run([python_exe, "generate.py", "--intent", "Create an S3 bucket with auto-delete"], check=True)
    
    print(">>> 2. Extracting CDK Instructions from FINAL_PROMPT.md...")
    with open("FINAL_PROMPT.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
    if not match:
        print("Error: Could not find python block in FINAL_PROMPT.md.")
        return
        
    cdk_code = match.group(1)
    
    print(">>> 3. Injecting generated code into testing ground...")
    stack_file = os.path.join("cdk-testing-ground", "cdk_testing_ground", "cdk_testing_ground_stack.py")
    with open(stack_file, "w", encoding="utf-8") as f:
        f.write(cdk_code)
        
    print(">>> 4. Linting injected stack code with flake8...")
    result_flake8 = subprocess.run([python_exe, "-m", "flake8", stack_file])
    if result_flake8.returncode == 0:
        print("Flake8: No critical issues found (Success).")
    else:
        print("Flake8: Issues detected!")
        
    print(">>> 5. Synthesizing CDK App...")
    synth_cmd = 'npx cdk synth -a "..\\\\venv\\\\Scripts\\\\python.exe app.py" --quiet'
    result_synth = subprocess.run(synth_cmd, cwd="cdk-testing-ground", shell=True)
    if result_synth.returncode == 0:
        print("CDK Synth: CloudFormation successfully generated.")
    else:
        print("CDK Synth: Compilation Failed!")
        
    print(">>> 6. Running Moto test suite in testing ground...")
    pytest_exe = os.path.join("..", "venv", "Scripts", "pytest")
    result_pytest = subprocess.run([python_exe, "-m", "pytest", "tests/unit/test_cdk_testing_ground_stack.py", "-v"], cwd="cdk-testing-ground")
    if result_pytest.returncode == 0:
        print("Pytest Moto: Validation complete and PASSED.")
    else:
        print("Pytest Moto: Tests failed!")
        
if __name__ == "__main__":
    main()
