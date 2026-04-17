import glob
import os
import re
from src.evaluators import _score_single_yaml

def validate_champions():
    champion_files = glob.glob(r"c:\Users\vjbel\hacks\inverse-prompt-gen\results\optimization\run_seed_champions\*.md")
    print(f"Discovered {len(champion_files)} Champion templates.")
    
    for file_path in champion_files:
        print(f"\n--- Validating: {os.path.basename(file_path)} ---")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract YAML block safely
        yaml_blocks = re.findall(r"```[a-zA-Z]*\s*(.*?)\s*```", content, re.DOTALL)
        if not yaml_blocks:
            print("  ❌ Could not extract YAML block.")
            continue
            
        yaml_blocks.sort(key=len, reverse=True)
        yaml_code = yaml_blocks[0].strip()
        
        # Test against our physical infrastructure validation
        score, rule_id, trace = _score_single_yaml(yaml_code, intent_text="Generic Validation")
        
        print(f"  Physical Score: {score:.2f}")
        if score < 1.0:
            print(f"  ❌ FAILURE TRACE: {trace}")
        else:
            print(f"  ✅ SUCCESS: Structurally passed cfn-lint and cfn-guard seamlessly!")

if __name__ == "__main__":
    validate_champions()
