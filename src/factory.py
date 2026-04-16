import dspy
from dspy.teleprompt import MIPROv2
from src.dspy_signatures import CDKPromptGenerator
from src.evaluators import cdk_compile_metric
from src.data_loader import load_training_intents, get_cdk_reference

import logging
logger = logging.getLogger(__name__)


class PromptFactory(dspy.Module):
    """DSPy module that generates CDK v2 instructional prompts.
    
    MIPROv2 optimizes the instructions and few-shot demonstrations
    inside the ChainOfThought wrapper to maximize compilation scores.
    """
    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(CDKPromptGenerator)

    def forward(self, architecture_intent, cdk_reference=""):
        if not cdk_reference:
            cdk_reference = get_cdk_reference(architecture_intent)
        return self.generator(
            architecture_intent=architecture_intent,
            cdk_reference=cdk_reference
        )


def train(auto="light", num_candidates=7, num_trials=15):
    """Run MIPROv2 optimization.
    
    Args:
        auto: MIPROv2 intensity ("light", "medium", "heavy")
        num_candidates: Number of instruction candidates to generate
        num_trials: Number of Bayesian search trials
    """
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in .env")
    
    lm = dspy.LM('openai/gpt-4o', api_key=api_key, temperature=0.7)
    dspy.configure(lm=lm)
    
    trainset = load_training_intents()
    if not trainset:
        raise ValueError("No training intents found. Create data/training_intents.json")
    
    logger.info("Starting MIPROv2 optimization")
    logger.info("  Auto: %s", auto)
    logger.info("  Candidates: %d", num_candidates)
    logger.info("  Trials: %d", num_trials)
    logger.info("  Training examples: %d", len(trainset))
    
    optimizer = MIPROv2(
        metric=cdk_compile_metric,
        auto=auto,
        num_candidates=num_candidates,
    )
    
    compiled = optimizer.compile(
        PromptFactory(),
        trainset=trainset,
        num_trials=num_trials,
    )
    
    # Save the optimized module
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "optimized_factory.json")
    compiled.save(output_path)
    logger.info("Optimized module saved to %s", output_path)
    
    return compiled


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
    
    auto = sys.argv[1] if len(sys.argv) > 1 else "light"
    train(auto=auto)
