import json
import logging
import requests
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

processor = BatchProcessor(event_type=EventType.SQS)

def record_handler(record: SQSRecord):
    """Processes a single SQS message inside the batch."""
    payload = json.loads(record.body)
    topic_id = payload["topicId"]
    url = payload["url"]

    logger.info(f"Ingesting topic: {topic_id} | URL: {url}")
    mark_source_processing(topic_id, url)

    try:
        clean_text = extract_content_from_url(url)
        chunks = chunk_text(clean_text)
        total_upserted = upsert_chunks(topic_id, url, chunks)
        mark_source_done(topic_id, url, total_upserted)
        logger.info(f"Successfully processed {url} ({total_upserted} chunks)")

    except ValueError as ve:
        # Permanent validation failure (e.g., SSRF block, size > 2MB, empty page)
        logger.warning(f"Permanent validation error for {url}: {str(ve)}")
        mark_source_failed(topic_id, url, str(ve))
        # Do NOT re-raise: let SQS delete the message

    except requests.exceptions.HTTPError as he:
        status_code = he.response.status_code if he.response is not None else 0
        if 400 <= status_code < 500 and status_code != 429:
            # Permanent HTTP 4xx error (404 Not Found, 403 Forbidden)
            logger.warning(f"Permanent HTTP {status_code} for {url}: {str(he)}")
            mark_source_failed(topic_id, url, f"HTTP {status_code} Error")
            # Do NOT re-raise: let SQS delete the message
        else:
            # Transient 429 Rate Limit or 5xx Server Error -> retry via SQS
            logger.error(f"Transient HTTP error for {url}: {str(he)}")
            mark_source_failed(topic_id, url, str(he))
            raise he

    except Exception as e:
        # Transient infrastructure error (MongoDB, Bedrock, Pinecone) -> retry via SQS
        logger.error(f"Transient failure for {url}: {str(e)}")
        mark_source_failed(topic_id, url, str(e))
        raise e

def lambda_handler(event: dict, context: LambdaContext):
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )