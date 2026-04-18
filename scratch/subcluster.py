import chromadb
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import logging

logging.getLogger('chromadb').setLevel(logging.ERROR)

def run_subclustering():
    try:
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection(name="sam_declarative_reference")
    except Exception as e:
        print("Failed to load ChromaDB:", e)
        return

    data = collection.get(include=["embeddings", "documents"])
    all_embeddings = data.get("embeddings", [])
    all_documents = data.get("documents", [])

    # Isolate specifically the Serverless specification API references (Cluster 2 equivalent)
    trace_embeddings = []
    trace_documents = []
    for emb, doc in zip(all_embeddings, all_documents):
        if "AWS::Serverless" in doc and "CRITICAL COMPILER WARNING" not in doc:
            trace_embeddings.append(emb)
            clean_doc = doc.replace("\n", " ").strip()
            trace_documents.append(clean_doc[:120] + "...")

    if len(trace_embeddings) < 10:
        print(f"Not enough error traces found ({len(trace_embeddings)}). Wait for optimization loop to inject more.")
        return

    X = np.array(trace_embeddings)
    print(f"=== SUB-CLUSTERING INITIATED ===\nExtracted {len(X)} specific compilation failure vectors explicitly bypassing main Specs.")

    best_score = -1
    best_k = 2

    # Dynamically find the best sub-cluster K
    print("\n[Sweeping K=2 to 10 for Peak Sub-Vector Separation]")
    for k in range(2, min(11, len(X))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k

    print(f"\n=> Optimal Semantic Trace Architecture detected at K={best_k} (Silhouette: {best_score:.3f})\n")

    # Run the best K and map the specific traces
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(X)
    
    for i in range(best_k):
        idx = np.where(labels == i)[0]
        print(f"--- Sub-Cluster {i} ({len(idx)} discrete errors) ---")
        # Print up to 3 samples from each matrix
        for n in range(min(3, len(idx))):
            print(f"   [Trace {n+1}]: {trace_documents[idx[n]]}")
        print("")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    run_subclustering()
