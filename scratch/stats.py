import re
import os
import collections

def analyze():
    log_path = r"c:\Users\vjbel\hacks\inverse-prompt-gen\results\optimization\run_1776396775\run_log.txt"
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.readlines()
        
    metrics = []
    errors = collections.Counter()
    stage_fails = collections.Counter()
    
    for line in content:
        if "Metric result:" in line:
            # [INFO] 2026-04-17 00:15:11 - Metric result: 1.000 (avg of 4 models)
            m = re.search(r"Metric result: ([\d\.]+)", line)
            if m: metrics.append(float(m.group(1)))
            
        if "402 Client Error" in line:
            errors["402 Payment Required"] += 1
            
        if "Stage 1 FAIL" in line: stage_fails["Stage 1 (Syntax)"] += 1
        if "Stage 2 FAIL" in line: stage_fails["Stage 2 (cfn-lint)"] += 1
        if "Stage 3 FAIL" in line: stage_fails["Stage 3 (cfn-guard)"] += 1
        
        if "Validation judge error" in line:
            errors["Semantic Judge Errors"] += 1
            
    print(f"Total metric evaluations: {len(metrics)}")
    if metrics:
        print(f"Last 10 metrics: {metrics[-10:]}")
        print(f"Max metric achieved: {max(metrics)}")
        
    print(f"Stage Fails: {dict(stage_fails)}")
    print(f"Errors: {dict(errors)}")

if __name__ == "__main__": analyze()
