import os
from datetime import datetime, timezone
from pymongo import MongoClient

mongo_client = MongoClient(os.environ["MONGODB_URI"])
db = mongo_client[os.getenv("MONGODB_DB_NAME", "exam_db")]
topics_col = db["knowledge_topics"]

def mark_source_processing(topic_id: str, url: str):
    topics_col.update_one(
        {"_id": topic_id, "sources.url": url},
        {"$set": {"sources.$.status": "PROCESSING", "updatedAt": datetime.now(timezone.utc)}}
    )

def mark_source_done(topic_id: str, url: str, chunk_count: int):
    # Update specific source
    topics_col.update_one(
        {"_id": topic_id, "sources.url": url},
        {
            "$set": {
                "sources.$.status": "DONE",
                "sources.$.chunkCount": chunk_count,
                "updatedAt": datetime.now(timezone.utc)
            },
            "$inc": {"totalChunks": chunk_count}
        }
    )
    
    # Check if all sources for this topic are DONE
    topic = topics_col.find_one({"_id": topic_id})
    if topic:
        all_done = all(src.get("status") == "DONE" for src in topic.get("sources", []))
        if all_done:
            topics_col.update_one(
                {"_id": topic_id},
                {"$set": {"status": "READY", "updatedAt": datetime.now(timezone.utc)}}
            )

def mark_source_failed(topic_id: str, url: str, error_msg: str):
    topics_col.update_one(
        {"_id": topic_id, "sources.url": url},
        {
            "$set": {
                "sources.$.status": "FAILED",
                "sources.$.error": error_msg,
                "updatedAt": datetime.now(timezone.utc)
            }
        }
    )