import os
import chromadb
from chromadb.config import Settings
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import numpy as np

# Path configurations
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")
OUT_DIR = "C:\\Users\\vjbel\\.gemini\\antigravity\\brain\\ca876cbc-f9df-4230-9f5b-47581ff7f146"

# Load ChromaDB
client = chromadb.PersistentClient(path=DB_PATH, settings=Settings(anonymized_telemetry=False))
try:
    collection = client.get_collection(name="sam_declarative_reference")
except:
    print("Failed to get collection.")
    exit(1)

# Fetch all embeddings
data = collection.get(include=['embeddings', 'documents'])
embeddings = data.get('embeddings')
documents = data.get('documents')

if not embeddings or len(embeddings) < 5:
    print(f"Not enough embeddings found. Only {len(embeddings) if embeddings else 0} elements.")
    exit(1)

X = np.array(embeddings)
print(f"Loaded {len(X)} embeddings for analysis.")

# Optimal K finding
k_values = range(2, min(15, len(X)))
best_k = 2
best_score = -1

for k in k_values:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(X)
    score = silhouette_score(X, labels)
    if score > best_score:
        best_score = score
        best_k = k

print(f"Optimally picked K based on Silhouette Score: {best_k} (Score: {best_score:.3f})")

# Reduce dimensions for visualization
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

targets = [3, 4, 12, best_k]
# Filter targets that are too large for our dataset
targets = [t for t in targets if t <= len(X)]
# Ensure best_k is uniquely included
targets = sorted(list(set(targets)))

fig, axes = plt.subplots(1, len(targets), figsize=(6 * len(targets), 5))
if len(targets) == 1:
    axes = [axes]

for i, k in enumerate(targets):
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    ax = axes[i]
    scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap='tab20', alpha=0.7)
    ax.set_title(f"K-Means (k={k}){ ' [OPTIMAL]' if k == best_k else '' }")
    ax.set_xlabel("PCA Component 1")
    ax.set_ylabel("PCA Component 2")
    
plt.tight_layout()
output_path = os.path.join(OUT_DIR, "kmeans_analysis.png")
plt.savefig(output_path, dpi=150)
print(f"SUCCESS: Plot saved to {output_path}")

# Display breakdown of the optimal clusters
kmeans_opt = KMeans(n_clusters=best_k, random_state=42, n_init=10)
opt_labels = kmeans_opt.fit_predict(X)
print("--- Optimal Cluster Document Sample ---")
for cluster_idx in range(best_k):
    print(f"\\nCluster {cluster_idx} samples:")
    docs_in_cluster = [doc for j, doc in enumerate(documents) if opt_labels[j] == cluster_idx]
    for d in docs_in_cluster[:2]:
        header = d[:100].replace("\\n", " ")
        print(f"  - {header}...")
