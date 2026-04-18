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
    labels = kmeans.fit_predict(X)

    # Construct and save centroids
    centroids = kmeans.cluster_centers_.tolist()
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"k": best_k, "centroids": centroids}, f)
    logger.info("Successfully exported mathematical centroids to %s", OUT_JSON)

    # 3. Update ChromaDB metadatas to bind the new cluster assignments
    updated_metadatas = []
    for i in range(len(ids)):
        meta = metadatas[i] if metadatas and i < len(metadatas) and metadatas[i] is not None else {}
        meta["cluster"] = int(labels[i])
        updated_metadatas.append(meta)

    # Write the updated metadata back to ChromaDB
    collection.update(
        ids=ids,
        metadatas=updated_metadatas
    )
    logger.info("Successfully bound K-Means routing clusters natively onto %d ChromaDB vectors.", len(ids))

if __name__ == "__main__":
    cluster_and_tag_db()
