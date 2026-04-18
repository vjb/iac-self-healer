import chromadb

try:
    # Try connecting to the local server running on port 8000
    client = chromadb.HttpClient(host="localhost", port=8000)
    print("Successfully connected to Chroma HTTP server.")
    
    # List collections
    collections = client.list_collections()
    if not collections:
        print("Connected, but found 0 collections.")
    else:
        print(f"Found {len(collections)} collections:")
        for col in collections:
            print(f"- {col.name}")
except Exception as e:
    print(f"Failed to connect or fetch data: {e}")
