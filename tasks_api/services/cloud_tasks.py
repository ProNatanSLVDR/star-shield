"""
Google Cloud Tasks service wrapper for enqueueing tasks.
"""

import json
import logging
from typing import Optional

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from django.conf import settings

logger = logging.getLogger(__name__)


def enqueue_review_fetch_task(
    etablissement_id: int,
    task_type: str,
    schedule_time: Optional[int] = None,
) -> Optional[str]:
    """
    Enqueue a review fetch task to Google Cloud Tasks.
    
    Args:
        etablissement_id: The ID of the Etablissement to fetch reviews for
        task_type: Either "fetch-all" or "fetch-refresh"
        schedule_time: Optional Unix timestamp for scheduled execution
    
    Returns:
        Task name if successful, None otherwise
    """
    try:
        # Initialize Cloud Tasks client
        client = tasks_v2.CloudTasksClient()
        
        # Get configuration from settings
        project_id = settings.CLOUD_TASKS_PROJECT_ID
        location = settings.CLOUD_TASKS_LOCATION
        queue_name = settings.CLOUD_TASKS_QUEUE_NAME
        api_base_url = settings.TASKS_API_BASE_URL
        auth_token = settings.TASKS_API_AUTH_TOKEN
        
        if not project_id:
            logger.error("CLOUD_TASKS_PROJECT_ID not configured")
            return None
        
        # Build queue path
        queue_path = client.queue_path(project_id, location, queue_name)
        
        # Determine endpoint based on task type
        if task_type == "fetch-all":
            endpoint = f"{api_base_url}/api/v1/tasks/reviews/fetch-all"
        elif task_type == "fetch-refresh":
            endpoint = f"{api_base_url}/api/v1/tasks/reviews/fetch-refresh"
        else:
            logger.error(f"Invalid task_type: {task_type}")
            return None
        
        # Create task payload
        payload = {
            "etablissement_id": etablissement_id
        }
        
        # Create task
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": endpoint,
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": json.dumps(payload).encode(),
            }
        }
        
        # Add authentication header if token is configured
        if auth_token:
            task["http_request"]["headers"]["Authorization"] = f"Bearer {auth_token}"
        
        # Add schedule time if provided
        if schedule_time:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromSeconds(schedule_time)
            task["schedule_time"] = timestamp
        
        # Create the task
        response = client.create_task(
            request={
                "parent": queue_path,
                "task": task,
            }
        )
        
        logger.info(
            f"Enqueued {task_type} task for Etablissement {etablissement_id}: {response.name}"
        )
        return response.name
        
    except Exception as e:
        logger.error(f"Error enqueueing Cloud Task: {e}", exc_info=True)
        return None

