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
        
    # Inject Dynamic Semantic Champions (Score >= 1.20)
    import glob
    import re
    md_files = glob.glob(os.path.join(PROJECT_ROOT, "results", "optimization", "run_*", "*.md"))
    for md_file in md_files:
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            score_match = re.search(r"\*\*Final Average Score:\*\* ([\d\.]+)", content)
            if score_match:
                score = float(score_match.group(1))
                if score >= 1.20:
                    intent_match = re.search(r"# Declarative AWS SAM Prompt: (.*)", content)
                    prompt_match = re.search(r"---\n+(.*?)\n+---", content, re.DOTALL)
                    if intent_match and prompt_match:
                        intent = intent_match.group(1).strip()
                        prompt_text = prompt_match.group(1).strip()
                        examples.append(
                            dspy.Example(
                                architecture_intent=intent,
                                sam_reference=get_sam_reference(intent),
                                prompt=prompt_text
                            ).with_inputs('architecture_intent', 'sam_reference')
                        )
                        logger.info("Injected semantic champion into trainset from %s", os.path.basename(md_file))
        except Exception as e:
            logger.debug("Failed parsing historical champion %s: %s", md_file, e)
            
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
    base_docs = "Use AWS SAM declarative syntax. Transform: AWS::Serverless-2016-10-31 is required."
    if collection and collection.count() > 0:
        try:
            import json
            import numpy as np
            from chromadb.utils import embedding_functions
            
            centroids_path = os.path.join(PROJECT_ROOT, "data", "kmeans_centroids.json")
            sub_cluster_0_id = None
            sub_cluster_1_id = None
            
            # Apply semantic KMS routing if centroids are natively available
            if os.path.exists(centroids_path):
                with open(centroids_path, "r") as f:
                    c_data = json.load(f)
                    sub_centroids_map = c_data.get("sub_centroids", {})
                    
                ef = embedding_functions.DefaultEmbeddingFunction()
                query_emb = np.array(ef([intent])[0])
                
                # Find best sub-cluster for Primary Cluster 0 (Documentation)
                if "0" in sub_centroids_map and sub_centroids_map["0"]:
                    sub_centroids_0 = np.array(sub_centroids_map["0"])
                    dist_0 = np.linalg.norm(sub_centroids_0 - query_emb, axis=1)
                    sub_cluster_0_id = int(np.argmin(dist_0))
                    
                # Find best sub-cluster for Primary Cluster 1 (Errors)
                if "1" in sub_centroids_map and sub_centroids_map["1"]:
                    sub_centroids_1 = np.array(sub_centroids_map["1"])
                    dist_1 = np.linalg.norm(sub_centroids_1 - query_emb, axis=1)
                    sub_cluster_1_id = int(np.argmin(dist_1))
            
            docs = []
            
            # Path 1: Ground Truth Documentation (Cluster 0)
            kwargs_0 = {
                "query_texts": [intent],
                "n_results": 2
            }
            if sub_cluster_0_id is not None:
                kwargs_0["where"] = {"$and": [{"cluster": 0}, {"sub_cluster": sub_cluster_0_id}]}
            else:
                kwargs_0["where"] = {"cluster": 0}
                
            res_0 = collection.query(**kwargs_0)
            if res_0 and res_0.get('documents') and res_0['documents'][0]:
                docs.extend(res_0['documents'][0])
                
            # Path 2: Hallucination Oracle / Error Bounds (Cluster 1)
            kwargs_1 = {
                "query_texts": [f"{intent} CRITICAL COMPILER WARNING constraints errors"],
                "n_results": 1
            }
            if sub_cluster_1_id is not None:
                kwargs_1["where"] = {"$and": [{"cluster": 1}, {"sub_cluster": sub_cluster_1_id}]}
            else:
                kwargs_1["where"] = {"cluster": 1}
                
            res_1 = collection.query(**kwargs_1)
            if res_1 and res_1.get('documents') and res_1['documents'][0]:
                docs.extend(res_1['documents'][0])
                
            if docs:
                base_docs = "\n\n---\n\n".join(docs)
                
        except Exception as e:
            logger.warning("ChromaDB routed query failed: %s", e)
            
    # Load physical WAFR .guard rules to enforce absolute bounds
    wafr_rules = ""
    guard_path = os.path.join(PROJECT_ROOT, "data", "aws-wafr-conformance-pack.guard")
    if os.path.exists(guard_path):
        with open(guard_path, "r", encoding="utf-8") as f:
            wafr_rules = f.read()

    strict_bounds = (
        "\n\n=== EXPLICIT COMPLIANCE & FRAMEWORK BOUNDS ===\n"
        "1. PHYSICAL WAFR RULES: You MUST guarantee your output inherently constructs the properties dictated by these rules to prevent cfn-guard crashes:\n"
        f"{wafr_rules}\n\n"
        "2. DEPRECATION TRAP: Runtimes like python3.9 are absolutely forbidden. You MUST explicitly enforce python3.12 or higher in your prompt constraints."
    )
    
    return base_docs + strict_bounds

def record_compiler_failure(intent: str, error_trace: str):
    """Embed an exhausted compiler failure back into ChromaDB to act as an oracle for the next trial."""
    collection = _get_chroma_collection()
    if not collection: return
    try:
        import hashlib
        import re
        
        # Sanitize random volatile RAM paths out of the trace so duplicate errors hash symmetrically
        # Utilizes explicit backslash literal limits to correctly match deep cfn-guard formatting strings flawlessly natively!
        sanitized_trace = re.sub(r'(?:\\\\?\?\\)?R:\\[a-zA-Z0-9_]+\\template\.yaml', '<RAM_DISK_FILE>', error_trace)
        
        # De-Noise the vector embedding bounds: Separate physical text summary from dense AST JSON Payload
        trace_parts = sanitized_trace.split("---", 1)
        plain_text_summary = trace_parts[0].strip()
        heavy_json_payload = trace_parts[1].strip() if len(trace_parts) > 1 else "{}"
        
        bug_id = "bug_" + hashlib.md5((intent + plain_text_summary).encode('utf-8')).hexdigest()[:15]
        warning_msg = f"CRITICAL COMPILER WARNING related to intent '{intent[:100]}...':\n"
        warning_msg += f"The following error previously occurred during SAM YAML execution:\n{plain_text_summary}\n"
        warning_msg += "Constraint: You MUST avoid the syntactic patterns that lead to this exception!"
        if len(warning_msg) > 1500: warning_msg = warning_msg[:1500] + "\n...[truncated]"
        
        # Use upsert to gracefully overwrite exact duplicate structural hashes natively
        # Safely offload massive JSON limits to metadatas array so NLP embedding models evaluate purely semantic constraints!
        collection.upsert(
            documents=[warning_msg], 
            ids=[bug_id],
            metadatas=[{"full_ast_json": heavy_json_payload[:5000]}]
        )
    except Exception as e:
        logger.warning(f"Oracle: Failed to record compiler failure to ChromaDB: {e}")
