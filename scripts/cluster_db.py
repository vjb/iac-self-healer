import os
import json
import logging
import chromadb
from chromadb.config import Settings
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
OUT_JSON = os.path.join(PROJECT_ROOT, "data", "kmeans_centroids.json")

def cluster_and_tag_db():
    try:
        client = chromadb.PersistentClient(path=DB_PATH, settings=Settings(anonymized_telemetry=False))
        collection = client.get_collection("sam_declarative_reference")
    except Exception as e:
        logger.error("Failed to connect to ChromaDB: %s", e)
        return

    data = collection.get(include=['embeddings', 'metadatas'])
    ids = data.get('ids', [])
    embeddings = data.get('embeddings', [])
    metadatas = data.get('metadatas', [])

    if embeddings is None or len(embeddings) < 5:
        logger.warning("Not enough embeddings (%d) to cluster. Minimally requires 5.", len(embeddings) if embeddings is not None else 0)
        return

    X = np.array(embeddings)
    logger.info("Loaded %d vectors from the database for clustering.", len(X))

    # Dynamically find the best K using Silhouette Score
    max_k = min(15, len(X) - 1)
    best_k = 2
    best_score = -1

    for k in range(2, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k

    logger.info("Optimal clusters derived: K=%d (Score: %.3f)", best_k, best_score)

    # Re-run with optimal K
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    primary_labels = kmeans.fit_predict(X)

    primary_centroids = kmeans.cluster_centers_.tolist()
    sub_centroids_map = {}
    
    # Layer 2: Hierarchical Sub-Clustering
    sub_labels = np.zeros(len(X), dtype=int)
    for i in range(best_k):
        indices = np.where(primary_labels == i)[0]
        if len(indices) < 5:
            sub_centroids_map[str(i)] = []
            continue
            
        sub_X = X[indices]
        max_sub_k = min(10, len(sub_X) - 1)
        best_sub_k = 2
        best_sub_score = -1
        
        for k in range(2, max_sub_k + 1):
            sub_km = KMeans(n_clusters=k, random_state=42, n_init='auto')
            l = sub_km.fit_predict(sub_X)
            score = silhouette_score(sub_X, l)
            if score > best_sub_score:
                best_sub_score = score
                best_sub_k = k
                
        sub_km = KMeans(n_clusters=best_sub_k, random_state=42, n_init=10)
        curr_sub_labels = sub_km.fit_predict(sub_X)
        for idx_array, real_idx in enumerate(indices):
            sub_labels[real_idx] = curr_sub_labels[idx_array]
            
        sub_centroids_map[str(i)] = sub_km.cluster_centers_.tolist()
        logger.info("  Primary %d -> Derived Sub-Clusters: %d", i, best_sub_k)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "k": best_k, 
            "centroids": primary_centroids,
            "sub_centroids": sub_centroids_map
        }, f)
    logger.info("Successfully exported hierarchical centroids to %s", OUT_JSON)

    # 3. Update ChromaDB metadatas to bind the new dual cluster assignments
    updated_metadatas = []
    for i in range(len(ids)):
        meta = metadatas[i] if metadatas and i < len(metadatas) and metadatas[i] is not None else {}
        meta["cluster"] = int(primary_labels[i])
        meta["sub_cluster"] = int(sub_labels[i])
        updated_metadatas.append(meta)

    # Write the updated metadata back to ChromaDB
    collection.update(
        ids=ids,
        metadatas=updated_metadatas
    )
    logger.info("Successfully bound K-Means routing clusters natively onto %d ChromaDB vectors.", len(ids))

if __name__ == "__main__":
    cluster_and_tag_db()
