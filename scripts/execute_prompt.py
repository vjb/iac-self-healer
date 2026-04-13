import os
import subprocess
import re
import sys

def main():
    import concurrent.futures
    import shutil
    import logging
    
    import sys
    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', stream=sys.stdout)
    logger = logging.getLogger(__name__)
    
    intent = sys.argv[1] if len(sys.argv) > 1 else "stand up a VM in us-central"
    temperature = sys.argv[2] if len(sys.argv) > 2 else "0.5"
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    N_VARIANTS = 3
    
    logger.info("Initializing Prompt Variants (Count: %d, Temp: %s) for intent: %s", N_VARIANTS, temperature, intent)
    variants = []
    
    import requests
    import json
    
    api_key = os.environ.get("OPENAI_API_KEY")

    def generate_single_variant(i):
        logger.debug("Executing Variant %d...", i+1)
        subprocess.run([python_exe, "generate.py", "--intent", intent, "--temperature", temperature, "--output_file", f"FINAL_PROMPT_{i}.md"], check=True)
        with open(f"FINAL_PROMPT_{i}.md", "r", encoding="utf-8") as f:
            content = f.read()
            
        student_prompt = f"""You are a Junior AWS CDK Coder. Look at the instructions string below, and produce the requested AWS CDK stack. 
Your output must be STRICTLY valid AWS CDK v2 Python code defining the 'CdkTestingGroundStack' class.
DO NOT include markdown block wrappers (like ```python). DO NOT include chat text. Just output pure Python code.
Instructions to Follow:\n\n{content}"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": student_prompt}],
            "temperature": 0.0
        }
        
        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            cdk_code = resp.json()['choices'][0]['message']['content'].strip()
            # clean up any accidental markdown wrapper from the student
            if cdk_code.startswith("```python"):
                cdk_code = cdk_code[len("```python"):].strip()
            if cdk_code.startswith("```"):
                cdk_code = cdk_code[3:].strip()
            if cdk_code.endswith("```"):
                cdk_code = cdk_code[:-3].strip()
        except Exception as e:
            logger.error("Student Agent failed on Variant %d. Error: %s", i+1, e)
            cdk_code = ""
            
        return i, content, cdk_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=N_VARIANTS) as executor:
        futures = {executor.submit(generate_single_variant, i): i for i in range(N_VARIANTS)}
        results = {}
        for future in concurrent.futures.as_completed(futures):
            idx, txt, code = future.result()
            results[idx] = (txt, code)
            
    for i in range(N_VARIANTS):
        content, cdk_code = results[i]
        tmp_path = f"tmp_stack_{i}.py"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(cdk_code)
        variants.append((i, tmp_path, cdk_code))
            
    logger.info("Linting variants concurrently with AST Validation and flake8.")
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
    
    logger.info("Champion Selected: Variant %d with %d syntax errors.", champion_i+1, champ_errors)
    if champ_errors > 0:
        logger.warning("Flake8: Syntax constraints violated")
        # We inject the flake8 stdout back into STDOUT so the main orchestrator reads it
        print("Flake8:\n" + champ_stdout.replace(f"tmp_stack_{champion_i}.py", "cdk-testing-ground/cdk_testing_ground/cdk_testing_ground_stack.py"))
    else:
        logger.info("Flake8: No critical syntax issues found (Success)")
        
    shutil.copy2(f"FINAL_PROMPT_{champion_i}.md", "FINAL_PROMPT.md")
    champion_code = next(v[2] for v in variants if v[0] == champion_i)
    
    logger.info("Injecting champion artifact into execution directory.")
    stack_file = os.path.join("cdk-testing-ground", "cdk_testing_ground", "cdk_testing_ground_stack.py")
    with open(stack_file, "w", encoding="utf-8") as f:
        f.write(champion_code)
        
    import shutil
    cdk_out_path = os.path.join("cdk-testing-ground", "cdk.out")
    if os.path.exists(cdk_out_path):
        # Surgically wipe any orphaned NodeJS threads holding the .cdk.out.lock
        subprocess.run('wmic process where "name=\'node.exe\' and commandline like \'%cdk%\'" call terminate', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(cdk_out_path, ignore_errors=True)
        
    # Bypassed Static Critic: Relying purely on physical compilation to prevent hallucination looping.

    logger.info("Synthesizing CDK Application")
    synth_cmd = 'npx cdk synth -a "..\\\\venv\\\\Scripts\\\\python.exe app.py" --quiet'
    result_synth = subprocess.run(synth_cmd, cwd="cdk-testing-ground", shell=True)
    if result_synth.returncode == 0:
        logger.info("CDK Synth: CloudFormation successfully generated.")
        print("CloudFormation successfully generated")
    else:
        logger.error("CDK Synth: Compilation Failed.")
        
    logger.info("Executing LocalStack container deployment.")
    deploy_env = os.environ.copy()
    deploy_env["AWS_ACCESS_KEY_ID"] = "test"
    deploy_env["AWS_SECRET_ACCESS_KEY"] = "test"
    deploy_env["AWS_DEFAULT_REGION"] = "us-east-1"
    
    deploy_cmd = 'npx cdklocal deploy --require-approval never -a "..\\\\venv\\\\Scripts\\\\python.exe app.py"'
    result_deploy = subprocess.run(deploy_cmd, cwd="cdk-testing-ground", shell=True, env=deploy_env)
    
    if result_deploy.returncode == 0:
        logger.info("LocalStack Deploy: Architecture physically validated and PASSED.")
        print("LocalStack Deploy: Architecture physically validated and PASSED.")
    else:
        logger.error("LocalStack Deploy: CloudFormation stack rollback or failure detected.")
if __name__ == "__main__":
    main()
