from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.tasks_api.services.queue_service import (
    create_google_cloud_task,
    enqueue_refresh_tasks,
)
from tests.factories import EtablissementFactory


@override_settings(
    GCP_PROJECT_ID="test-project",
    GCP_PROJECT_REGION="us-central1",
    CLOUD_TASKS_SERVICE_ACCOUNT="test@test.iam.gserviceaccount.com",
    TASKS_API_QUEUE_NAME="test-queue",
    TASKS_API_BASE_URL="http://localhost:8001",
)
class TestCreateGoogleCloudTask(TestCase):
    @patch("apps.tasks_api.services.queue_service.tasks_v2.CloudTasksClient")
    def test_creates_task_with_correct_payload(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.task_path.return_value = "projects/test/locations/us/queues/q/tasks/t"
        mock_client.queue_path.return_value = "projects/test/locations/us/queues/q"

        create_google_cloud_task(
            queue="test-queue",
            url="http://localhost:8001/v1/fetch-refresh",
            payload={"etablissement_id": 1},
            task_id="test-task",
        )

        mock_client.create_task.assert_called_once()

    @patch("apps.tasks_api.services.queue_service.tasks_v2.CloudTasksClient")
    def test_creates_task_with_schedule(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.task_path.return_value = "projects/test/locations/us/queues/q/tasks/t"
        mock_client.queue_path.return_value = "projects/test/locations/us/queues/q"

        create_google_cloud_task(
            queue="test-queue",
            url="http://localhost:8001/v1/fetch-refresh",
            payload={"etablissement_id": 1},
            task_id="test-task",
            scheduled_seconds_from_now=60,
        )

        mock_client.create_task.assert_called_once()


@override_settings(
    GCP_PROJECT_ID="test-project",
    GCP_PROJECT_REGION="us-central1",
    CLOUD_TASKS_SERVICE_ACCOUNT="test@test.iam.gserviceaccount.com",
    TASKS_API_QUEUE_NAME="test-queue",
    TASKS_API_BASE_URL="http://localhost:8001",
)
class TestEnqueueRefreshTasks(TestCase):
    @patch("apps.tasks_api.services.queue_service.create_google_cloud_task")
    def test_enqueues_for_all_etablissements(self, mock_create_task):
        EtablissementFactory()
        EtablissementFactory()

        result = enqueue_refresh_tasks()

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["enqueued"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(mock_create_task.call_count, 2)

    @patch("apps.tasks_api.services.queue_service.create_google_cloud_task")
    def test_returns_summary_dict(self, mock_create_task):
        EtablissementFactory()

        result = enqueue_refresh_tasks()

        self.assertIn("total", result)
        self.assertIn("enqueued", result)
        self.assertIn("failed", result)
        self.assertIn("errors", result)

    @patch("apps.tasks_api.services.queue_service.create_google_cloud_task")
    def test_logs_errors_on_failure(self, mock_create_task):
        mock_create_task.side_effect = Exception("Cloud Tasks error")
        EtablissementFactory()

        result = enqueue_refresh_tasks()

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["enqueued"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(len(result["errors"]), 1)

    @patch("apps.tasks_api.services.queue_service.create_google_cloud_task")
    def test_empty_etablissements(self, mock_create_task):
        result = enqueue_refresh_tasks()

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["enqueued"], 0)
        mock_create_task.assert_not_called()
