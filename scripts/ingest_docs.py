import os
import json
import urllib.request
import urllib.error
import chromadb
import uuid
import sys

def chunk_markdown(text, chunk_size=1500, overlap=200):
    """Mechanically split markdown files into overlapping semantic chunks."""
    chunks = []
    i = 0
    while i < len(text):
        end = i + chunk_size
        if end < len(text):
            # Try to find a clean line break if possible
            last_newline = text.rfind('\n', i, end)
            if last_newline != -1 and last_newline > i + (chunk_size // 2):
                end = last_newline
        chunks.append(text[i:end].strip())
        i = end - overlap
    return chunks

def main():
    print("[SYSTEM] Booting AWS CDK v2 Documentation Harvester...")
    
    db_path = os.path.join(os.getcwd(), "chroma_db")
    print(f"[SYSTEM] Initializing Persistent ChromaDB Lexicon at: {db_path}")
    chroma_client = chromadb.PersistentClient(path=db_path, settings=chromadb.Settings(anonymized_telemetry=False))
    collection = chroma_client.get_or_create_collection(name="cdk_v2_docs")
    
    api_url = "https://api.github.com/repos/awsdocs/aws-cdk-guide/contents/v2/guide"
    
    print(f"[CRAWLER] Fetching repository tree: {api_url}")
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Antigravity-IaC-Healer'})
    
    try:
        with urllib.request.urlopen(req) as response:
            tree = json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f">>> [FATAL ERROR] Failed to fetch GitHub API. You may be rate limited. {e}")
        sys.exit(1)
        
    md_files = [x for x in tree if x.get('name', '').endswith('.md')]
    print(f"[CRAWLER] Discovered {len(md_files)} official markdown documents.")
    
    total_chunks_embedded = 0
    
    for file_node in md_files:
        name = file_node['name']
        download_url = file_node['download_url']
        print(f" -> Harvesting {name}...")
        
        try:
            doc_req = urllib.request.Request(download_url, headers={'User-Agent': 'Antigravity-IaC-Healer'})
            with urllib.request.urlopen(doc_req) as res:
                content = res.read().decode('utf-8')
                
            chunks = chunk_markdown(content)
            
            # Embed chunks
            if chunks:
                collection.add(
                    documents=chunks,
                    metadatas=[{"source": name, "doc_type": "official_guide"} for _ in chunks],
                    ids=[f"{name}_chunk_{i}_{uuid.uuid4().hex[:6]}" for i in range(len(chunks))]
                )
                total_chunks_embedded += len(chunks)
                
        except Exception as e:
            print(f"    [!] Failed to harvest {name}: {e}")
            
    print(f"[SYSTEM] HARVEST COMPLETE! Successfully mapped {total_chunks_embedded} semantic vectors into the Persistent Lexicon.")

if __name__ == "__main__":
    main()
