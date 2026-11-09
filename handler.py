import json
import logging
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext

from scraper import extract_content_from_url
from chunker import chunk_text
from vector_service import upsert_chunks
from db import mark_source_processing, mark_source_done, mark_source_failed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configured for SQS batch processing
processor = BatchProcessor(event_type=EventType.SQS)

def record_handler(record: SQSRecord):
    """Processes a single SQS message inside the batch."""
    payload = json.loads(record.body)
    topic_id = payload["topicId"]
    url = payload["url"]

    logger.info(f"Ingesting topic: {topic_id} | URL: {url}")
    mark_source_processing(topic_id, url)

    try:
        # 1. Scrape & sanitize
        clean_text = extract_content_from_url(url)

        # 2. Chunk text
        chunks = chunk_text(clean_text)

        # 3. Embed & upsert to Pinecone topic namespace
        total_upserted = upsert_chunks(topic_id, url, chunks)

        # 4. Update MongoDB status to DONE/READY
        mark_source_done(topic_id, url, total_upserted)
        logger.info(f"Successfully processed {url} ({total_upserted} chunks)")

    except Exception as e:
        logger.error(f"Failed to process {url}: {str(e)}")
        mark_source_failed(topic_id, url, str(e))
        # Raising an exception here tells Powertools this specific message failed
        # SQS will only retry this record, not the entire batch
        raise e

def lambda_handler(event: dict, context: LambdaContext):
    """Entry point delegating to Powertools partial batch handler."""
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )