import os
import random
import time
import json
import subprocess
import shutil

def main():
    info_dir = os.path.join("info", "aws startup prompts")
    if not os.path.exists(info_dir):
        print(f"Error: {info_dir} not found.")
        return
        
    all_files = [f for f in os.listdir(info_dir) if f.endswith(".md")]
    random.seed(1337)
    subset = random.sample(all_files, min(3, len(all_files)))
    
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    python_exe = os.path.join("venv", "Scripts", "python.exe")
    
    print(f"Starting Benchmark... Validating subset of {len(subset)} prompts.")
    
    for i, file_name in enumerate(subset):
        base_name = file_name.replace(".md", "")
        intent = f"{base_name}"
        
        print(f"\n========================================================")
        print(f"[{i+1}/{len(subset)}] Testing Intent: {intent}")
        print(f"========================================================")
        
        target_dir = os.path.join(results_dir, base_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Save starting raw prompt structure
        shutil.copy2(os.path.join(info_dir, file_name), os.path.join(target_dir, "starting_prompt.md"))
        
        try:
            print(f">>> Triggering Execution Gauntlet...")
            result = subprocess.run(
                [python_exe, os.path.join("scripts", "execute_prompt.py"), intent],
                capture_output=True,
                text=True
            )
            stdout, stderr = result.stdout, result.stderr
            
            with open(os.path.join(target_dir, "gauntlet_logs.txt"), "w", encoding="utf-8") as f:
                f.write(stdout)
                f.write("\n\n=== STDERR ===\n")
                f.write(stderr)
                
            # Copy isolated AI prompt payload
            if os.path.exists("FINAL_PROMPT.md"):
                shutil.copy2("FINAL_PROMPT.md", os.path.join(target_dir, "FINAL_PROMPT.md"))
                
            # Copy extracted CDK Stack 
            stack_path = os.path.join("cdk-testing-ground", "cdk_testing_ground", "cdk_testing_ground_stack.py")
            if os.path.exists(stack_path):
                shutil.copy2(stack_path, os.path.join(target_dir, "cdk_testing_ground_stack.py"))

            # Calculate continuous evaluator metrics based on gauntlet traces
            score_data = {
                "flake8_pass": "Issues detected" not in stdout,
                "cdk_synth_pass": "CloudFormation successfully generated" in stdout,
                "moto_test_pass": "Validation complete and PASSED" in stdout,
                "open_api_rate_limit": "Too Many Requests" in stdout
            }
            
            # Simple weighting: 40% Synth, 40% Pytest Moto, 20% Flake8 formatting
            final_score = 0
            if score_data["cdk_synth_pass"]: final_score += 40
            if score_data["moto_test_pass"]: final_score += 40
            if score_data["flake8_pass"]: final_score += 20
            
            score_data["total_score"] = final_score
            
            with open(os.path.join(target_dir, "score.json"), "w", encoding="utf-8") as f:
                json.dump(score_data, f, indent=4)
                
            print(f"Metrics Complete. Score: {final_score}/100")
            print(f"Rate Limit Safe: {not score_data['open_api_rate_limit']}")

            # Sleep 15s to respect OpenAI Free-Tier RPM (Rate Per Minute) constraints
            if i < len(subset) - 1:
                print(f"Waiting 15 seconds to flush TPM bucket...")
                time.sleep(15)

        except Exception as e:
            print(f"Execution crashed: {str(e)}")

if __name__ == "__main__":
    main()
