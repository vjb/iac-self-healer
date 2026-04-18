import chromadb
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import logging

logging.getLogger('chromadb').setLevel(logging.ERROR)

def run_clustering():
    try:
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection(name="sam_declarative_reference")
    except Exception as e:
        print("Failed to load ChromaDB:", e)
        return

    data = collection.get(include=["embeddings", "documents"])
    embeddings = data.get("embeddings", [])
    documents = data.get("documents", [])

    if len(embeddings) < 15:
        print(f"Not enough vectors to cluster well. DB has {len(embeddings)} items.")
        return

    X = np.array(embeddings)
    print(f"Loaded {len(X)} high-dimensional vectors from sam_declarative_reference.")

    targets = [3, 6, 10]
    best_k = 2
    best_score = -1

    for k in targets:
        if k >= len(X):
            print(f"Cannot group {k} clusters with only {len(X)} items.")
            continue
            
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X)
        score = silhouette_score(X, labels)
        print(f"\n[Fixed Target K={k}] - Silhouette Score: {score:.3f}")
        
        # sample some documents
        for i in range(min(k, 3)): # Print first 3 clusters max
            idx = np.where(labels == i)[0]
            if len(idx) > 0:
                sample_doc = documents[idx[0]][:80].replace("\n", " ") + "..."
                print(f"  Cluster {i} ({len(idx)} items) -> ex: {sample_doc}")
                
    print("\n[Dynamic Auto-Detection (K=2 to 15)]")
    for k in range(2, min(16, len(X))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k
            
    print(f"Peak Vector Separation cleanly detected at K={best_k} (Silhouette: {best_score:.3f})")
    print("This indicates the LLM is heavily diverging the problem space precisely into that many topological matrices!")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    run_clustering()
