"""
Prompt Optimizer Entry Point

Runs MIPROv2 optimization across training intents, then exports
the best prompts as submission-ready markdown documents.
"""
import os
import sys
import json
import time
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def optimize(auto="light", num_candidates=7, num_trials=15):
    """Run full MIPROv2 optimization and export results."""
    from src.factory import PromptFactory, train
    from src.data_loader import load_training_intents, get_cdk_reference
    import dspy
    
    run_timestamp = int(time.time())
    results_dir = os.path.join("results", "optimization", f"run_{run_timestamp}")
    os.makedirs(results_dir, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("PROMPT OPTIMIZER — MIPROv2")
    logger.info("=" * 60)
    logger.info("Run ID: %d", run_timestamp)
    logger.info("Results dir: %s", results_dir)
    
    # Phase 1: Optimize
    logger.info("Phase 1: Running MIPROv2 optimization...")
    compiled = train(auto=auto, num_candidates=num_candidates, num_trials=num_trials)
    
    # Phase 2: Generate prompts from optimized module
    logger.info("Phase 2: Generating prompts from optimized module...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    lm = dspy.LM('openai/gpt-4o', api_key=api_key, temperature=0.5)
    dspy.configure(lm=lm)
    
    intents = load_training_intents()
    
    for i, example in enumerate(intents):
        intent = example.architecture_intent
        logger.info("Generating prompt %d/%d: %s", i + 1, len(intents), intent[:50])
        
        try:
            cdk_ref = get_cdk_reference(intent)
            result = compiled(architecture_intent=intent, cdk_reference=cdk_ref)
            prompt_text = getattr(result, 'prompt', '')
            
            if prompt_text:
                # Export as submission-ready markdown
                submission = _format_submission(intent, prompt_text)
                
                safe_name = intent[:40].replace(" ", "_").replace("/", "_").lower()
                output_path = os.path.join(results_dir, f"prompt_{i}_{safe_name}.md")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(submission)
                logger.info("  → Saved to %s", output_path)
            else:
                logger.warning("  → Empty prompt field. Available fields: %s",
                             [f for f in dir(result) if not f.startswith('_')])
        except Exception as e:
            logger.error("  → Failed: %s", e, exc_info=True)
    
    # Save run metadata
    metadata = {
        "run_id": run_timestamp,
        "auto": auto,
        "num_candidates": num_candidates,
        "num_trials": num_trials,
        "num_intents": len(intents),
        "timestamp_end": int(time.time())
    }
    with open(os.path.join(results_dir, "run_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info("=" * 60)
    logger.info("Optimization complete. Results in: %s", results_dir)
    logger.info("=" * 60)


def _format_submission(intent: str, prompt_text: str) -> str:
    """Format a prompt as a hackathon-ready BUIDL submission document."""
    return f"""# AWS CDK v2 Prompt: {intent}

## Category
Infrastructure as Code (IaC) — AWS CDK v2 Python

## AWS Services Used
_Extracted from the architecture intent and prompt content._

## Prerequisites
- Python 3.8 or higher
- Node.js 20+ (required for AWS CDK CLI and JSII runtime)
- AWS CDK v2 CLI: `npm install -g aws-cdk`
- AWS account with appropriate IAM permissions
- Python packages: `aws-cdk-lib`, `constructs`

## Prompt

> Copy and paste the following prompt into any AI assistant (ChatGPT, Claude, etc.)
> to generate a complete, working AWS CDK v2 Python stack.

---

{prompt_text}

---

## Troubleshooting

### Common Errors

1. **`ModuleNotFoundError: No module named 'aws_cdk'`**
   - Install: `pip install aws-cdk-lib constructs`

2. **`Cannot find module 'aws-cdk-lib'`**
   - Run: `npm install aws-cdk-lib`

3. **`Error: This app contains no stacks`**
   - Ensure your `app.py` instantiates the stack and calls `app.synth()`

4. **`jsii.errors.JavaScriptError: ... is not a constructor`**
   - Check import paths — CDK v2 uses `from aws_cdk import aws_X`, not `from aws_cdk.core import X`

5. **`SubnetType.PRIVATE is not valid`**
   - Use `SubnetType.PRIVATE_WITH_EGRESS` instead (CDK v2 renamed this)

## Verification

```bash
# Synthesize the CloudFormation template (no deployment needed)
cdk synth

# Deploy to your AWS account
cdk deploy
```
"""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run MIPROv2 prompt optimization")
    parser.add_argument("--auto", default="light", choices=["light", "medium", "heavy"],
                        help="MIPROv2 optimization intensity")
    parser.add_argument("--candidates", type=int, default=7,
                        help="Number of instruction candidates")
    parser.add_argument("--trials", type=int, default=15,
                        help="Number of Bayesian search trials")
    args = parser.parse_args()
    
    optimize(auto=args.auto, num_candidates=args.candidates, num_trials=args.trials)
