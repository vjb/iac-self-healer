import os
import sys
import json
import subprocess
import shutil
import time
import requests
import builtins
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt

try:
    import chromadb
except ImportError:
    pass

def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)

@retry(wait=wait_exponential(multiplier=1, min=2, max=60), stop=stop_after_attempt(5))
def _post_openai_request(headers, payload):
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if resp.status_code == 429:
        print(">>> [META-ANALYZER] Rate Limit Exceeded (HTTP 429). Encountering exponential backoff...")
    resp.raise_for_status()
    return resp

def invoke_meta_analyzer(stderr_trace, rag_collection=None):
    """
    Acts as the DSPy Reflection Agent. Parses a Python stack trace or CloudFormation 
    synthesis crash, deduces the root cause, and generates an absolute behavioral constraint.
    """
    print(">>> [META-ANALYZER] Reflecting on stack trace...")
    print(f"[META-ANALYZER] Parsing Error: {stderr_trace[:200]}...")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "Always use aws_lambda.Code.from_inline() for lambdas."
        
    retrieved_context = ""
    if rag_collection:
        try:
            results = rag_collection.query(query_texts=[stderr_trace[-300:]], n_results=1)
            docs = results.get('documents')
            if docs and len(docs) > 0 and len(docs[0]) > 0:
                retrieved_context = f"\\n<RETRIEVED_DOCUMENTATION_MAP>\\n{docs[0][0]}\\n</RETRIEVED_DOCUMENTATION_MAP>\\nNote: Prioritize giving constraints based on the exact path in this retrieved AWS CDK context.\\n"
        except Exception as e:
            pass
            
    system_prompt = """You are the Meta-Analyzer in a Self-Healing ML loop.
The Generator Agent just failed to synthesize AWS CDK Python code.
Analyze the following crash log and output up to THREE highly specific constraints instructing the Generator Agent what it MUST NEVER do again, or what it MUST do to fix it.

CRITICAL RULES:
1. NEVER output generic advice like "check the documentation for the right attribute" or "ensure correct versions".
2. If the log is an AttributeError or ModuleNotFoundError, you MUST provide the exact correct Python module path replacement. If you do not 100% know the correct path, tell the Generator to "Delete the failing resource and fallback to inline AWS Lambda architecture".
3. Constraints must be absolute mathematical rules.

Format exactly like this, separated by newlines:
Never use X; you must use Y.
Always import Z when using W.

Do not include any other text, markdown, or bullet points.""" + retrieved_context

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Crash Log:\n{stderr_trace}"}
            ],
            "max_tokens": 150
        }
        resp = _post_openai_request(headers, payload)
        constraints_text = resp.json()['choices'][0]['message']['content']
        constraints = [c.strip().lstrip('-').lstrip('*').strip() for c in constraints_text.split("\n") if c.strip()]
        return constraints[:3]
    except Exception as e:
        print(f"Meta-Analyzer API failed: {e}")
        return ["Never use local file paths or from_asset; always use inline lambda code."]


def main():
    load_dotenv()
    
    target_intent = sys.argv[1] if len(sys.argv) > 1 else "Container Orchestration"
    
    # Check and clear stop flag
    if os.path.exists("stop_flag.txt"):
        os.remove("stop_flag.txt")
        
    run_timestamp = int(time.time())
    results_dir = os.path.join("results", "learning_loop", f"run_{run_timestamp}")
    os.makedirs(results_dir, exist_ok=True)
    
    run_summary_path = os.path.join(results_dir, "run_summary.json")
    run_stats = {
        "metadata": {
            "target_intent": target_intent,
            "timestamp_start": run_timestamp,
            "platform": sys.platform,
            "python_version": sys.version
        },
        "status": "running",
        "iterations": []
    }
    with open(run_summary_path, "w", encoding="utf-8") as f:
        json.dump(run_stats, f, indent=4)
    
    # Reset constraints
    if os.path.exists("learned_constraints.txt"):
        os.remove("learned_constraints.txt")
        
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    max_iterations = 8
    
    rag_collection = None
    if 'chromadb' in sys.modules:
        try:
            print("[SYSTEM] Initializing Offline ChromaDB RAG Lexicon...")
            chroma_client = chromadb.Client()
            rag_collection = chroma_client.get_or_create_collection(name="cdk_v2_docs")
            
            cdk_docs = [
                "AWS CDK v2 ApplicationLoadBalancer: The ApplicationLoadBalancer class has been moved to aws_elasticloadbalancingv2. Use aws_elasticloadbalancingv2.ApplicationLoadBalancer.",
                "AWS CDK v2 LatestAmazonLinux: MachineImage.latestAmazonLinux is deprecated, you must use MachineImage.latestAmazonLinux2.",
                "AWS CDK v2 SubnetType: Use aws_ec2.SubnetType.PRIVATE_WITH_EGRESS or PRIVATE_ISOLATED instead of PRIVATE.",
                "AWS CDK v2 DynamoDB RemovalPolicy: Do not use aws_dynamodb.RemovalPolicy. Instead, use aws_cdk.RemovalPolicy.DESTROY.",
                "AWS CDK v2 Lambda Asset Path: To use a local lambda code folder, use aws_lambda.Code.from_asset('lambda'). If the asset throws ENOTEMPTY or NotFound, it means the lambda directory is missing. Fallback to inline: aws_lambda.Code.from_inline('def handler(event, context): pass').",
                "AWS CDK v2 RDS Keyword Arguments: aws_rds.DatabaseInstance does not accept 'security_group'. You must pass an array to 'security_groups=[my_sg]'."
            ]
            rag_collection.add(documents=cdk_docs, ids=[f"doc_{i}" for i in range(len(cdk_docs))])
        except Exception as e:
            print(f"[SYSTEM] RAG Init failed: {e}")
            
    score_history = []
    current_temperature = 0.5
    
    print(f"===============================================================", flush=True)
    print(f"INITIATING AUTONOMOUS SELF-HEALING OPTIMIZER (MIPRO SIMULATION)", flush=True)
    print(f"Target: '{target_intent}'", flush=True)
    print(f"===============================================================\n", flush=True)

    for i in range(max_iterations):
        iter_dir = os.path.join(results_dir, f"iteration_{i}")
        os.makedirs(iter_dir, exist_ok=True)
        
        print(f"--- ITERATION {i} ---")
        import threading
        
        # Prevent ghost CDK locking bugs from previous crashed iterations
        cdk_out_path = os.path.join("cdk-testing-ground", "cdk.out")
        if os.path.exists(cdk_out_path):
            shutil.rmtree(cdk_out_path, ignore_errors=True)
        
        # 1. Execute the Pipeline
        print(f">>> [GENERATOR] Attempting to synthesize infrastructure (Temp={current_temperature})...")
        process = subprocess.Popen(
            [python_exe, "-u", os.path.join("scripts", "execute_prompt.py"), target_intent, str(current_temperature)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        stdout_lines = []
        stderr_lines = []
        
        def read_stream(stream, lines_list):
            for line in stream:
                print(line, end="")
                lines_list.append(line)
                
        t1 = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines))
        t2 = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines))
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        process.wait()
        
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        
        with open(os.path.join(iter_dir, "gauntlet_logs.txt"), "w", encoding="utf-8") as f:
            f.write(stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(stderr)
            
        final_prompt_txt = ""
        if os.path.exists("FINAL_PROMPT.md"):
            shutil.copy2("FINAL_PROMPT.md", os.path.join(iter_dir, "FINAL_PROMPT.md"))
            with open("FINAL_PROMPT.md", "r", encoding="utf-8") as pf:
                final_prompt_txt = pf.read()
            
        generated_code_txt = ""
        stack_file = os.path.join("cdk-testing-ground", "cdk_testing_ground", "cdk_testing_ground_stack.py")
        if os.path.exists(stack_file):
            shutil.copy2(stack_file, os.path.join(iter_dir, "generated_stack.py"))
            with open(stack_file, "r", encoding="utf-8") as cf:
                generated_code_txt = cf.read()

        # Fractional Scoring Algorithm
        score = 0
        issues = 0
        
        if "Flake8:" in stdout:
            score = 15 # Base points for successful python synthesis
            # Deduct points for syntax errors, minimum 0 additive
            lines_with_error = [l for l in stdout.split("\n") if "cdk-testing-ground" in l and (": E" in l or ": F" in l or ": W" in l)]
            issues = len(lines_with_error)
            score += max(20 - (issues * 2), 0)
            
        cdk_success = "CloudFormation successfully generated" in stdout
        test_success = "Validation complete and PASSED" in stdout
        
        if cdk_success:
            score += 35
            
        if test_success:
            score += 30
            
        # Hard override if score is somehow perfect here
        if test_success and issues == 0:
            score = 100
            
        print(f">>> [ENVIRONMENT] Gauntlet Score Evaluated: {score}/100")
        
        score_history.append(score)
        if len(score_history) > 3:
            score_history.pop(0)

        current_temperature = 0.5
        if len(score_history) >= 3 and (max(score_history) - min(score_history)) < 5 and score < 100:
            print(f">>> [ORCHESTRATOR] STAGNATION DETECTED! SCORE LOCKED IN LOCAL MINIMA (History: {score_history}).")
            print(f">>> [ORCHESTRATOR] INITIATING KERNEL KICKSTART PROTOCOL (T=1.2) FOR ARCHITECTURE SHAKEUP.")
            current_temperature = 1.2
            score_history.clear()
            
        iter_stats = {
            "iteration": i,
            "score": score,
            "flake8_issues": issues,
            "cdk_synth_success": cdk_success,
            "pytest_success": test_success,
            "generated_code_snapshot": generated_code_txt,
            "orchestrator_prompt": final_prompt_txt,
            "new_constraints": [],
            "extracted_stderr": ""
        }
        
        if score == 100:
            print(f"\n[SUCCESS] The architecture has successfully converged and compiled!")
            print(f"[SUCCESS] Final constraint state saved in: {iter_dir}")
            run_stats["status"] = "success"
            run_stats["metadata"]["timestamp_end"] = int(time.time())
            run_stats["iterations"].append(iter_stats)
            with open(run_summary_path, "w", encoding="utf-8") as f:
                json.dump(run_stats, f, indent=4)
            break
            
        print(f"\n>>> [ENVIRONMENT] CRITICAL SYNTAX OR SYNTH FAILURE DETECTED.")
        print(f">>> [ENVIRONMENT] Extracting Traceback...")
        
        # 2. Aggressive Noise Filtering for Traceback
        lines = stderr.split("\n")
        filtered_trace = []
        for line in lines:
            if "!!" in line or "UserWarning:" in line or "warnings.warn(" in line or "PytestDeprecationWarning" in line:
                continue
            if len(line.strip()) == 0:
                continue
            filtered_trace.append(line)
            
        traceback_segment = "\n".join(filtered_trace[-40:]) # Send only the last 40 lines which usually contains the exact `Exception:` trace
        iter_stats["extracted_stderr"] = traceback_segment
        
        # 3. Meta Analyzer Reflects and Writes Rules
        new_rules = invoke_meta_analyzer(traceback_segment, rag_collection)
        iter_stats["new_constraints"] = new_rules
        
        with open("learned_constraints.txt", "a", encoding="utf-8") as f:
            for rule in new_rules:
                print(f">>> [META-ANALYZER] Generated New Constraint: '{rule}'")
                f.write(f"- {rule}\n")
            
        with open(os.path.join(iter_dir, "learned_constraints_update.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(new_rules))
            
        # Write to run JSON summary
        run_stats["iterations"].append(iter_stats)
        run_stats["metadata"]["timestamp_current"] = int(time.time())
        with open(run_summary_path, "w", encoding="utf-8") as f:
            json.dump(run_stats, f, indent=4)
            
        if os.path.exists("stop_flag.txt"):
            print(f"\n>>> [SYSTEM] Stop flag received! Gracefully shutting down...")
            os.remove("stop_flag.txt")
            run_stats["status"] = "halted"
            run_stats["metadata"]["timestamp_end"] = int(time.time())
            with open(run_summary_path, "w", encoding="utf-8") as f:
                json.dump(run_stats, f, indent=4)
            break
            
        if i < max_iterations - 1:
            print(f">>> [ORCHESTRATOR] Applying new constraint logic to context...")
            print(f">>> [ORCHESTRATOR] Flushing API rate limit queues (15s sleep)...\n")
            time.sleep(15)
        else:
            print(f"\n[FAILED] Reached max iterations ({max_iterations}) without converging.")
            run_stats["status"] = "failed"
            run_stats["metadata"]["timestamp_end"] = int(time.time())
            with open(run_summary_path, "w", encoding="utf-8") as f:
                json.dump(run_stats, f, indent=4)

if __name__ == "__main__":
    main()
