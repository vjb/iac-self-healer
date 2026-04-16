"""
Data Loader for CDK v2 Reference Documentation and Training Intents.

- Loads architecture intents as DSPy Examples for MIPROv2 training.
- Queries ChromaDB for CDK v2 reference documentation to ground prompts.
- Populates ChromaDB from scraped data files if empty.
"""
import os
import json
import glob
import logging

import dspy

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
TRAINING_INTENTS_PATH = os.path.join(PROJECT_ROOT, "data", "training_intents.json")
CDK_REFERENCE_DIR = os.path.join(PROJECT_ROOT, "data", "cdk_v2_reference")
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
        
        # Get CDK reference for this intent
        cdk_ref = get_cdk_reference(intent)
        
        examples.append(
            dspy.Example(
                architecture_intent=intent,
                cdk_reference=cdk_ref
            ).with_inputs('architecture_intent', 'cdk_reference')
        )
    
    logger.info("Loaded %d training intents", len(examples))
    return examples


def _get_chroma_collection():
    """Get or create the ChromaDB collection, populated with CDK v2 docs."""
    try:
        import chromadb
    except ImportError:
        logger.warning("chromadb not installed. Reference grounding disabled.")
        return None
    
    try:
        client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        collection = client.get_or_create_collection(name="cdk_v2_docs")
        
        if collection.count() == 0:
            _seed_chroma(collection)
        
        return collection
    except Exception as e:
        logger.error("ChromaDB initialization failed: %s", e)
        return None


def _seed_chroma(collection):
    """Seed ChromaDB with scraped CDK v2 reference documentation."""
    logger.info("Seeding ChromaDB with CDK v2 reference docs...")
    
    docs = []
    ids = []
    doc_id = 0
    
    # Load all markdown files from cdk_v2_reference/
    for md_file in glob.glob(os.path.join(CDK_REFERENCE_DIR, "*.md")):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split into chunks by ## headers for better retrieval
            sections = content.split("\n## ")
            for i, section in enumerate(sections):
                if len(section.strip()) < 20:
                    continue
                
                # Add back the ## prefix for non-first sections
                if i > 0:
                    section = "## " + section
                
                # Split further if section is too large (>1000 chars)
                if len(section) > 1000:
                    # Split by code blocks
                    subsections = section.split("```")
                    current_chunk = ""
                    for j, sub in enumerate(subsections):
                        if j % 2 == 1:  # Inside code block
                            current_chunk += "```" + sub + "```"
                        else:
                            current_chunk += sub
                        
                        if len(current_chunk) > 800 or j == len(subsections) - 1:
                            if current_chunk.strip():
                                docs.append(current_chunk.strip())
                                ids.append(f"ref_{doc_id}")
                                doc_id += 1
                            current_chunk = ""
                else:
                    docs.append(section.strip())
                    ids.append(f"ref_{doc_id}")
                    doc_id += 1
                    
        except Exception as e:
            logger.warning("Failed to read %s: %s", md_file, e)
    
    if docs:
        # ChromaDB has a batch limit; add in chunks of 40
        for batch_start in range(0, len(docs), 40):
            batch_docs = docs[batch_start:batch_start + 40]
            batch_ids = ids[batch_start:batch_start + 40]
            collection.add(documents=batch_docs, ids=batch_ids)
        
        logger.info("Seeded ChromaDB with %d document chunks", len(docs))
    else:
        logger.warning("No reference documents found in %s", CDK_REFERENCE_DIR)


def get_cdk_reference(intent: str) -> str:
    """
    Query ChromaDB for CDK v2 documentation relevant to the given intent.
    
    Falls back to loading full reference files if ChromaDB is unavailable.
    """
    collection = _get_chroma_collection()
    
    if collection and collection.count() > 0:
        try:
            results = collection.query(
                query_texts=[intent],
                n_results=5
            )
            documents = results.get('documents', [[]])
            if documents and documents[0]:
                return "\n\n---\n\n".join(documents[0])
        except Exception as e:
            logger.warning("ChromaDB query failed: %s. Falling back to file load.", e)
    
    # Fallback: load the import paths and migration pitfalls directly
    reference = ""
    for filename in ["import_paths.md", "migration_pitfalls.md"]:
        filepath = os.path.join(CDK_REFERENCE_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                reference += f"\n\n{f.read()}"
    
    return reference[:3000] if reference else "Use AWS CDK v2 Python syntax. Import from aws_cdk, not aws_cdk.core."
