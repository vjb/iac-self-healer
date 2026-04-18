import os
import json
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "diverse_error_training_set.jsonl")

def extract_diverse_bugs():
    try:
        import chromadb
        from sklearn.cluster import HDBSCAN
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
            
    if len(bug_docs) < 2:
        logger.warning(f"Not enough structural bugs ({len(bug_docs)}) to form physical clusters.")
        return

    logger.info(f"Isolated {len(bug_docs)} pure execution trace algorithms. Initiating HDBSCAN Density Modeling...")
    embeddings_matrix = np.array(bug_embeddings)
    
    # Execute native density-based dynamic modeling
    clusterer = HDBSCAN(min_cluster_size=2)
    labels = clusterer.fit_predict(embeddings_matrix)
    
    unique_clusters = set(labels)
    if -1 in unique_clusters:
        logger.info(f"Filtered {list(labels).count(-1)} noisy vector outliers successfully.")
        unique_clusters.remove(-1)
        
    num_clusters = len(unique_clusters)
    if num_clusters == 0:
        logger.warning("HDBSCAN failed to identify native clusters over standard bounds. Adjust min_cluster_size.")
        return
        
    logger.info(f"Dynamically discovered {num_clusters} mathematically distinct error clusters natively!")
    
    diverse_training_examples = []
    
    for c_id in unique_clusters:
        # Locate all vectors mapped physically to this cluster
        cluster_indices = np.where(labels == c_id)[0]
        cluster_points = embeddings_matrix[cluster_indices]
        
        # Compute geometric center natively
        centroid = cluster_points.mean(axis=0)
        
        # Calculate standard euclidean distance vector across the local density boundary
        distances = np.linalg.norm(cluster_points - centroid, axis=1)
        
        # Isolate the exact literal trace nearest to the semantic center of the failure cluster
        closest_local_idx = np.argmin(distances)
        global_idx = cluster_indices[closest_local_idx]
        
        diverse_training_examples.append(bug_docs[global_idx])

    logger.info("Successfully extracted mathematically diverse subsets!")
    
    # Export to strict jsonl format
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for idx, doc in enumerate(diverse_training_examples):
            json_line = json.dumps({"cluster": idx, "oracle_trace": doc})
            f.write(json_line + "\n")
            
    logger.info(f"Dumped {len(diverse_training_examples)} training vectors to {OUTPUT_PATH}")
    
if __name__ == "__main__":
    extract_diverse_bugs()
