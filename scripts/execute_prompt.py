import os
import subprocess
import re
import sys

def main():
    import concurrent.futures
    import shutil
    
    intent = sys.argv[1] if len(sys.argv) > 1 else "stand up a VM in us-central"
    temperature = sys.argv[2] if len(sys.argv) > 2 else "0.5"
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    N_VARIANTS = 3
    
    print(f">>> 1. Generating Prompt Variants (Best of {N_VARIANTS}, Temp={temperature}) for: {intent}")
    variants = []
    
    for i in range(N_VARIANTS):
        print(f"       -> Generating Variant {i+1}...")
        subprocess.run([python_exe, "generate.py", "--intent", intent, "--temperature", temperature], check=True)
        shutil.copy2("FINAL_PROMPT.md", f"FINAL_PROMPT_{i}.md")
        
        with open(f"FINAL_PROMPT_{i}.md", "r", encoding="utf-8") as f:
            content = f.read()
            
        match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
        if match:
            cdk_code = match.group(1)
            tmp_path = f"tmp_stack_{i}.py"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(cdk_code)
            variants.append((i, tmp_path, cdk_code))
        else:
            print(f"       -> [ERROR] Variant {i+1} failed Python structure extraction.")
            
    print(f">>> 2. Linting variants concurrently with AST Shield and flake8...")
    def run_linter(variant_info):
        import ast
        i, path, cdk_code = variant_info
        
        # AST Validation Shield
        ast_issues = ""
        try:
            tree = ast.parse(cdk_code)
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            has_stack = any('Stack' in [getattr(b, 'id', '') for b in c.bases] for c in classes)
            if not has_stack:
                ast_issues = f"{path}:1:1: AST001 No AWS CDK Stack inheritance found.\\n"
        except Exception as e:
            ast_issues = f"{path}:1:1: AST000 Failed to parse AST: {str(e)}\\n"

        res = subprocess.run([python_exe, "-m", "flake8", "--select=E9,F63,F7,F82", path], capture_output=True, text=True)
        
        stdout_combined = ast_issues + res.stdout
        error_count = len(stdout_combined.split('\n')) - 1 if stdout_combined.strip() else 0
        if ast_issues:
            error_count += 999  # Disqualify immediately
            
        return i, error_count, stdout_combined, res.returncode
        
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=N_VARIANTS) as executor:
        futures = {executor.submit(run_linter, v): v for v in variants}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            
    # Find Champion
    results.sort(key=lambda x: x[1]) # Sort by error count
    champion_i, champ_errors, champ_stdout, champ_code = results[0]
    
    print(f">>> 3. Champion Selected: Variant {champion_i+1} with {champ_errors} syntax errors.")
    if champ_errors > 0:
        print(f"Flake8: Issues detected!")
        # We inject the flake8 stdout back into STDOUT so the main orchestrator reads it
        print(champ_stdout.replace(f"tmp_stack_{champion_i}.py", "cdk-testing-ground/cdk_testing_ground/cdk_testing_ground_stack.py"))
    else:
        print(f"Flake8: No critical issues found (Success).")
        
    shutil.copy2(f"FINAL_PROMPT_{champion_i}.md", "FINAL_PROMPT.md")
    champion_code = next(v[2] for v in variants if v[0] == champion_i)
    
    print(">>> 4. Injecting champion generated code into testing ground...")
    stack_file = os.path.join("cdk-testing-ground", "cdk_testing_ground", "cdk_testing_ground_stack.py")
    with open(stack_file, "w", encoding="utf-8") as f:
        f.write(champion_code)
        
    print(">>> 5. Synthesizing CDK App...")
    synth_cmd = 'npx cdk synth -a "..\\\\venv\\\\Scripts\\\\python.exe app.py" --quiet'
    result_synth = subprocess.run(synth_cmd, cwd="cdk-testing-ground", shell=True)
    if result_synth.returncode == 0:
        print("CDK Synth: CloudFormation successfully generated.")
    else:
        print("CDK Synth: Compilation Failed!")
        
    print(">>> 6. Running LocalStack Architecture Synthesis...")
    deploy_env = os.environ.copy()
    deploy_env["AWS_ACCESS_KEY_ID"] = "test"
    deploy_env["AWS_SECRET_ACCESS_KEY"] = "test"
    deploy_env["AWS_DEFAULT_REGION"] = "us-east-1"
    
    deploy_cmd = 'npx cdklocal deploy --require-approval never -a "..\\\\venv\\\\Scripts\\\\python.exe app.py"'
    result_deploy = subprocess.run(deploy_cmd, cwd="cdk-testing-ground", shell=True, env=deploy_env)
    
    if result_deploy.returncode == 0:
        print("LocalStack Deploy: Architecture physically validated and PASSED.")
    else:
        print("LocalStack Deploy: CloudFormation stack rollback or failure detected!")
if __name__ == "__main__":
    main()
