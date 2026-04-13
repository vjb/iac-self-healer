import argparse
import dspy
from src.factory import PromptFactory
from src.data_loader import get_aws_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True, help="The core infrastructure requirement.")
    parser.add_argument("--temperature", type=float, default=0.5, help="Temperature for generative randomness.")
    parser.add_argument("--output_file", type=str, default="", help="Specific filepath destination to write FINAL_PROMPT output to.")
    args = parser.parse_args()
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    lm = dspy.LM('openai/gpt-4o', api_key=api_key, temperature=args.temperature)
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
    out_file = args.output_file if args.output_file else "FINAL_PROMPT.md"
    with open(out_file, "w", encoding='utf-8') as f:
        f.write(output)
        
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Generation complete. Output allocated to %s", out_file)

if __name__ == "__main__":
    main()
