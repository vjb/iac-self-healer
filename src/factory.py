import dspy
from dspy.teleprompt import MIPROv2
from src.dspy_signatures import SAMPromptGenerator
from src.evaluators import sam_compile_metric
from src.data_loader import load_training_intents, get_sam_reference

import logging
logger = logging.getLogger(__name__)

def get_vectorized_feedback(rule_id: str) -> str:
    """Queries ChromaDB to retrieve deterministic constraints based on CFN error codes."""
    import chromadb
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="sam_declarative_reference")
        
        results = collection.query(
            query_texts=[rule_id],
            n_results=1
        )
        if results and results["documents"] and results["documents"][0]:
            return results["documents"][0][0]
    except Exception as e:
        logger.warning("Failed to retrieve vector feedback for %s: %s", rule_id, e)
        
    return f"Resolve the declarative constraint structural failure associated with {rule_id}."


class PromptFactory(dspy.Module):
    """DSPy module that generates AWS SAM instructional prompts."""
    def __init__(self):
        super().__init__()
        self.generator = dspy.ChainOfThought(SAMPromptGenerator)

    def forward(self, architecture_intent, sam_reference=""):
        if not sam_reference:
            sam_reference = get_sam_reference(architecture_intent)
        return self.generator(
            architecture_intent=architecture_intent,
            sam_reference=sam_reference
        )


def train(auto="light", num_candidates=7, num_trials=15, resume=False, results_dir=None):
    """Run MIPROv2 optimization.
    
    Args:
        auto: MIPROv2 intensity ("light", "medium", "heavy")
        num_candidates: Number of instruction candidates to generate
        num_trials: Number of Bayesian search trials
        resume: Whether to resume from optimized_factory.json weights
        results_dir: The timestamped directory to land the json checkpoints
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
    
    output_path = os.path.join(results_dir, "optimized_factory.json") if results_dir else os.path.join(os.path.dirname(os.path.dirname(__file__)), "optimized_factory.json")
    
    # Initialize the base factory and inject previous weights if resuming an optimization loop
    base_factory = PromptFactory()
    if resume:
        champion_id = None
        state_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".optimizer_state.json")
        if os.path.exists(state_file):
            import json
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    champion_id = state.get("champion_run_id")
            except Exception as e:
                logger.warning("Failed to read .optimizer_state.json: %s", e)
                
        if champion_id:
            resume_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results", "optimization", f"run_{champion_id}", "optimized_factory.json")
        else:
            resume_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "optimized_factory.json")
            
        if os.path.exists(resume_path):
            logger.info("Found checkpoint at %s. Loading weights to bootstrap MIPROv2 compilation!", resume_path)
            try:
                base_factory.load(resume_path)
            except Exception as e:
                logger.warning("Failed to load previous weights from %s: %s. Starting from scratch.", resume_path, e)
        else:
            logger.warning("Attempted to resume but no checkpoint found at %s", resume_path)
            
    if auto:
        # Auto mode controls num_candidates and num_trials internally
        optimizer = MIPROv2(
            metric=sam_compile_metric,
            auto=auto,
            verbose=True,
        )
        compiled = optimizer.compile(
            base_factory,
            trainset=trainset,
        )
    else:
        # Manual mode: user controls candidates and trials
        optimizer = MIPROv2(
            metric=sam_compile_metric,
            num_candidates=num_candidates,
            verbose=True,
        )
        compiled = optimizer.compile(
            base_factory,
            trainset=trainset,
            num_trials=num_trials,
        )
    
    # Save the optimized module using DSPy 3.x native .save()
    if not results_dir:
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "optimized_factory.json")
    compiled.save(output_path)
    logger.info("Optimized module saved to %s", output_path)
    
    return compiled


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')
    
    auto = sys.argv[1] if len(sys.argv) > 1 else "light"
    train(auto=auto)
