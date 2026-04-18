import os
import json
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "diverse_error_training_set.jsonl")

def extract_diverse_bugs(num_clusters=5):
    try:
        import chromadb
        from sklearn.cluster import KMeans
    except ImportError:
        logger.error("scikit-learn or chromadb missing. Run: pip install scikit-learn chromadb numpy")
        return

    logger.info("Initializing ChromaDB connection...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(name="sam_declarative_reference")
    
    # Extract complete vector payload
    data = collection.get(include=["embeddings", "documents"])
    
    # Filter explicitly for `bug_` documents to isolate generative errors perfectly
    bug_docs = []
    bug_embeddings = []
    
    for _id, doc, emb in zip(data['ids'], data['documents'], data['embeddings']):
        if _id.startswith('bug_'):
            bug_docs.append(doc)
            bug_embeddings.append(emb)
            
    if len(bug_docs) < num_clusters:
        logger.warning(f"Not enough structural bugs ({len(bug_docs)}) to form {num_clusters} diverse clusters.")
        num_clusters = max(1, len(bug_docs))
        if num_clusters == 0:
            logger.info("No Oracle bug constraints found. Exiting.")
            return

    logger.info(f"Isolated {len(bug_docs)} pure execution trace algorithms. Initiating KMeans(clusters={num_clusters})...")
    embeddings_matrix = np.array(bug_embeddings)
    
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    kmeans.fit(embeddings_matrix)
    
    diverse_training_examples = []
    
    for i in range(num_clusters):
        cluster_center = kmeans.cluster_centers_[i]
        
        # Calculate standard euclidean distance vector across the boundary
        distances = np.linalg.norm(embeddings_matrix - cluster_center, axis=1)
        
        # Isolate the exact literal trace nearest to the semantic center of the failure cluster
        closest_index = np.argmin(distances)
        diverse_training_examples.append(bug_docs[closest_index])

    logger.info("Successfully extracted mathematically diverse subsets!")
    
    # Export to strict jsonl format
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for idx, doc in enumerate(diverse_training_examples):
            json_line = json.dumps({"cluster": idx, "oracle_trace": doc})
            f.write(json_line + "\n")
            
    logger.info(f"Dumped {len(diverse_training_examples)} training vectors to {OUTPUT_PATH}")
    
if __name__ == "__main__":
    extract_diverse_bugs()
