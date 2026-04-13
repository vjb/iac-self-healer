import argparse
import dspy
from src.factory import PromptFactory
from src.data_loader import get_aws_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True, help="The core infrastructure requirement.")
    parser.add_argument("--temperature", type=float, default=0.5, help="Temperature for generative randomness.")
    args = parser.parse_args()
    
    lm = dspy.LM('anthropic.claude-v2:1', api_base='http://localhost:11434', api_key='mock', temperature=args.temperature)
    dspy.configure(lm=lm)
    
    factory = PromptFactory()
    try:
        factory.load("optimized_factory.json")
    except Exception:
        pass
        
    context = get_aws_context()
    
    context = get_aws_context()
    topology_locked_intent = args.intent + "\nCRITICAL TOPOLOGY LOCK: You must retain the exact underlying topological architecture (e.g. EC2, RDS, VPC) defined within the user intent. Do not completely substitute base layout components or pivot the architecture model just to avoid a constraint. Maintain the fundamental architecture requested."
    prediction = factory(intent=topology_locked_intent, aws_strict_context=context)
    
    output = f"""# AWS Prompt Output
## Prerequisites
{prediction.prerequisites}

## Use Case
{prediction.use_case}

## Instructions
```python
{prediction.core_instructions}
```

## Troubleshooting
{prediction.troubleshooting}
"""
    with open("FINAL_PROMPT.md", "w", encoding='utf-8') as f:
        f.write(output)
        
    print("ALL PHASES COMPLETE. AWAITING COMMAND TO INITIATE TRAINING.")

if __name__ == "__main__":
    main()
