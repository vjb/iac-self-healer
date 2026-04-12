import os
import subprocess

def continuous_aws_metric(gold, prediction, trace=None):
    """
    Score from 0.0 to 1.0 based on Format, Syntax, Security, and Functional oracles.
    """
    score = 0.0
    
    # 1. Format (10%)
    text = (
        getattr(prediction, "core_instructions", "") + 
        getattr(prediction, "prerequisites", "") + 
        getattr(prediction, "use_case", "") + 
        getattr(prediction, "troubleshooting", "")
    )
    
    if "Prerequisites" in text and "Use Case" in text and "Troubleshooting" in text:
        score += 0.1
        
    # 2. Syntax Oracle (30%)
    # In real execution, extract CDK code, write to cdk-testing-ground/app.py, run cdk synth
    code_snippet = getattr(prediction, "core_instructions", "")
    if "import aws_cdk" in code_snippet: 
        # mock compilation success
        score += 0.3
        
        # 3. Security Oracle (30%)
        # mock cdk-nag success
        score += 0.3
        
        # 4. Functional Oracle (30%)
        # mock LocalStack instantiation 
        score += 0.3
        
    return score
