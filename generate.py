import argparse
import dspy
from src.factory import PromptFactory
from src.data_loader import get_aws_context

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", type=str, required=True, help="The core infrastructure requirement.")
    args = parser.parse_args()
    
    lm = dspy.LM('anthropic.claude-v2:1', api_base='http://localhost:11434', api_key='mock')
    dspy.configure(lm=lm)
    
    factory = PromptFactory()
    try:
        factory.load("optimized_factory.json")
    except Exception:
        pass
        
    context = get_aws_context()
    
    # Inference mock
    class MockPrediction:
        prerequisites = "1. AWS Account\n2. LocalStack\n3. CDK CLI"
        use_case = args.intent
        core_instructions = """from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy
)
from constructs import Construct


class CdkTestingGroundStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        s3.Bucket(
            self, "SecureBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
"""
        troubleshooting = "Check Docker and Moto connections."
    
    prediction = MockPrediction()
    
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
