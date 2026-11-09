import json
import os
import boto3
from pinecone import Pinecone

bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

def generate_embedding(text: str) -> list[float]:
    payload = json.dumps({"inputText": text,
                          "dimensions": 1024,
                          "normalize": True})  # Forcing dimension to match Pinecone index configuration
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=payload
    )
    response_body = json.loads(response["body"].read().decode("utf-8"))
    return response_body["embedding"]


def upsert_chunks(topic_id: str, url: str, chunks: list[str]) -> int:
    namespace_index = index.Index(os.environ["PINECONE_INDEX_NAME"]) if hasattr(index, "Index") else index
    vectors_to_upsert = []

    for i, chunk in enumerate(chunks):
        vector_id = f"{topic_id}#{hash(url)}#{i}"
        embedding = generate_embedding(chunk)
        
        metadata = {
            "topicId": topic_id,
            "sourceUrl": url,
            "chunkIndex": i,
            "text": chunk[:1000] # store reference text excerpt
        }
        
        vectors_to_upsert.append({
            "id": vector_id,
            "values": embedding,
            "metadata": metadata
        })

    # Batch upsert into topic-isolated namespace
    index.upsert(vectors=vectors_to_upsert, namespace=topic_id)
    return len(vectors_to_upsert)