"""
Data Loader for AWS SAM Reference Documentation and Training Intents.

- Loads architecture intents as DSPy Examples for MIPROv2 training.
- Queries ChromaDB for AWS SAM reference documentation to ground prompts.
"""
import os
import json
import logging
import dspy

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TRAINING_INTENTS_PATH = os.path.join(PROJECT_ROOT, "data", "training_intents.json")
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

def load_training_intents():
    """Load architecture intents from data/training_intents.json as DSPy Examples."""
    if not os.path.exists(TRAINING_INTENTS_PATH):
        logger.warning("No training intents file found at %s", TRAINING_INTENTS_PATH)
        return []
    
    with open(TRAINING_INTENTS_PATH, "r", encoding="utf-8") as f:
        intents = json.load(f)
    
    examples = []
    for item in intents:
        intent = item.get("architecture_intent", "")
        if not intent:
            continue
        
        sam_ref = get_sam_reference(intent)
        examples.append(
            dspy.Example(
                architecture_intent=intent,
                sam_reference=sam_ref
            ).with_inputs('architecture_intent', 'sam_reference')
        )
    return examples

def _get_chroma_collection():
    try:
        import chromadb
    except ImportError:
        logger.warning("chromadb not installed.")
        return None
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(name="sam_declarative_reference")
        return collection
    except Exception as e:
        logger.warning("ChromaDB initialization failed: %s", e)
        return None

def get_sam_reference(intent: str) -> str:
    """Query ChromaDB for AWS SAM documentation relevant to the given intent."""
    collection = _get_chroma_collection()
    if collection and collection.count() > 0:
        try:
            results = collection.query(query_texts=[intent], n_results=5)
            documents = results.get('documents', [[]])
            if documents and documents[0]:
                return "\n\n---\n\n".join(documents[0])
        except Exception as e:
            logger.warning("ChromaDB query failed: %s", e)
    return "Use AWS SAM declarative syntax. Transform: AWS::Serverless-2016-10-31 is required."

def record_compiler_failure(intent: str, error_trace: str):
    """Embed an exhausted compiler failure back into ChromaDB to act as an oracle for the next trial."""
    collection = _get_chroma_collection()
    if not collection: return
    try:
        import hashlib
        bug_id = "bug_" + hashlib.md5((intent + error_trace).encode('utf-8')).hexdigest()[:15]
        warning_msg = f"CRITICAL COMPILER WARNING related to intent '{intent[:100]}...':\n"
        warning_msg += f"The following error previously occurred during SAM YAML execution:\n{error_trace}\n"
        warning_msg += "Constraint: You MUST avoid the syntactic patterns that lead to this exception!"
        if len(warning_msg) > 1500: warning_msg = warning_msg[:1500] + "\n...[truncated]"
        collection.add(documents=[warning_msg], ids=[bug_id])
    except Exception as e:
        logger.warning(f"Oracle: Failed to record compiler failure to ChromaDB: {e}")
