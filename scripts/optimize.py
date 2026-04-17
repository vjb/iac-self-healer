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
    level=logging.DEBUG,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


def optimize(auto="light", num_candidates=7, num_trials=15, resume=False):
    """Run full MIPROv2 optimization and export results."""
    from src.factory import PromptFactory, train
    from src.data_loader import load_training_intents, get_sam_reference
    import dspy
    
    run_timestamp = int(time.time())
    results_dir = os.path.join("results", "optimization", f"run_{run_timestamp}")
    os.makedirs(results_dir, exist_ok=True)
    
    # Attach telemetry to specific run folder
    fh = logging.FileHandler(os.path.join(results_dir, "run_log.txt"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logging.getLogger().addHandler(fh)
    
    logger.info("=" * 60)
    logger.info("PROMPT OPTIMIZER — MIPROv2")
    logger.info("=" * 60)
    logger.info("Run ID: %d", run_timestamp)
    logger.info("Results dir: %s", results_dir)
    
    # Phase 1: Optimize
    logger.info("Phase 1: Running MIPROv2 optimization...")
    compiled = train(auto=auto, num_candidates=num_candidates, num_trials=num_trials, resume=resume, results_dir=results_dir)
    
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
            sam_ref = get_sam_reference(intent)
            result = compiled(architecture_intent=intent, sam_reference=sam_ref)
            prompt_text = getattr(result, 'prompt', '')
            
            if prompt_text:
                from src.evaluators import evaluate_prompt_with_details
                logger.info("  → Evaluating prompt to capture detailed scores and error traces...")
                score, details = evaluate_prompt_with_details(prompt_text)
                
                # Export as submission-ready markdown
                submission = _format_submission(intent, prompt_text, score, details)
                
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


def _format_submission(intent: str, prompt_text: str, score: float = 0.0, details: list = None) -> str:
    """Format a prompt as a hackathon-ready BUIDL submission document."""
    base_markdown = f"""# Declarative AWS SAM Prompt: {intent}

## Category
Infrastructure as Code (IaC) — AWS SAM (YAML)

## AWS Services Used
_Extracted from the architecture intent and prompt content._

## Prerequisites
- AWS SAM CLI installed
- `cfn-lint` installed checking CloudFormation configurations
- `cfn-guard` installed for strict security compliance verification

## Prompt

> Copy and paste the following prompt into any AI assistant (ChatGPT, Claude, etc.)
> to generate a complete, structurally sound AWS SAM YAML template.

---

{prompt_text}

---

## Troubleshooting

### Common Errors

1. **`[Lint E1001] Top level template section not valid`**
   - Ensure `Transform: AWS::Serverless-2016-10-31` is declared at the absolute root of the document.

2. **`[Lint E3002] Resource properties are missing`**
   - Check the specific resource block for missing required attributes (e.g., CodeUri, Handler).

3. **`cfn-guard violation`**
   - Your architecture breached strict HIPAA or NIST compliance bounds. Verify KMS encryption patterns and VPC subnets.

## Verification

```bash
# Verify static structure without deployment
cfn-lint template.yaml

# Verify security bounds
cfn-guard validate --data template.yaml
```
"""
    error_section = "\\n## Evaluation Trace & Scores\\n"
    error_section += f"**Final Average Score:** {score:.3f}\\n\\n"
    
    if details:
        for d in details:
            error_section += f"### Model: {d['model']} (Score: {d['score']})\\n"
            if d.get('error'):
                error_section += f"```text\\n{d['error']}\\n```\\n\\n"
            else:
                error_section += f"> Synthesized without critical errors.\\n\\n"
                
    return base_markdown + error_section


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run MIPROv2 prompt optimization")
    parser.add_argument("--auto", default="light", choices=["light", "medium", "heavy"],
                        help="MIPROv2 optimization intensity")
    parser.add_argument("--candidates", type=int, default=7,
                        help="Number of instruction candidates")
    parser.add_argument("--trials", type=int, default=15,
                        help="Number of Bayesian search trials")
    parser.add_argument("--resume", action="store_true",
                        help="Resume optimization from existing optimized_factory.json weights")
    args = parser.parse_args()
    
    optimize(auto=args.auto, num_candidates=args.candidates, num_trials=args.trials, resume=args.resume)
