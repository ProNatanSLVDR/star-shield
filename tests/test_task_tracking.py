from django.test import TestCase

from apps.tasks_api.api.task_tracking import TaskTracker
from apps.tasks_api.models import TaskExecution
from tests.factories import EtablissementFactory, TaskExecutionFactory


class TestTaskExecutionModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory()

    def test_mark_running(self):
        task = TaskExecutionFactory(etablissement=self.etab, status="pending")
        task.mark_running()
        task.refresh_from_db()
        self.assertEqual(task.status, "running")

    def test_mark_success(self):
        task = TaskExecutionFactory(etablissement=self.etab, status="running")
        task.mark_success()
        task.refresh_from_db()
        self.assertEqual(task.status, "success")
        self.assertIsNotNone(task.completed_at)

    def test_mark_error(self):
        task = TaskExecutionFactory(etablissement=self.etab, status="running")
        task.mark_error("Something went wrong")
        task.refresh_from_db()
        self.assertEqual(task.status, "error")
        self.assertEqual(task.error_message, "Something went wrong")
        self.assertIsNotNone(task.completed_at)

    def test_str_representation(self):
        task = TaskExecutionFactory(etablissement=self.etab, task_type="fetch_reviews")
        self.assertIn("fetch_reviews", str(task))
        self.assertIn(self.etab.title, str(task))

    def test_default_status_is_pending(self):
        task = TaskExecution.objects.create(
            task_type="fetch_stats",
            etablissement=self.etab,
        )
        self.assertEqual(task.status, "pending")


class TestTaskTracker(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory(active=True)

    def test_executes_functions_in_order(self):
        call_order = []

        def func1(etab):
            call_order.append("func1")

        def func2(etab):
            call_order.append("func2")

        tracker = TaskTracker("fetch_reviews", self.etab.id)
        tracker.execute([func1, func2])

        self.assertEqual(call_order, ["func1", "func2"])
        self.assertIsNotNone(tracker.task_execution)
        tracker.task_execution.refresh_from_db()
        self.assertEqual(tracker.task_execution.status, "success")

    def test_creates_task_execution(self):
        tracker = TaskTracker("fetch_stats", self.etab.id)
        tracker.execute([lambda etab: None])

        self.assertIsNotNone(tracker.task_execution)
        self.assertEqual(tracker.task_execution.task_type, "fetch_stats")
        self.assertEqual(tracker.task_execution.etablissement, self.etab)

    def test_marks_error_on_exception(self):
        msg = "Task failed"

        def failing_func(etab):
            raise RuntimeError(msg)

        tracker = TaskTracker("fetch_reviews", self.etab.id)
        with self.assertRaises(RuntimeError):
            tracker.execute([failing_func])

        tracker.task_execution.refresh_from_db()
        self.assertEqual(tracker.task_execution.status, "error")
        self.assertIn("Task failed", tracker.task_execution.error_message)

    def test_raises_value_error_for_missing_etablissement(self):
        tracker = TaskTracker("fetch_reviews", 99999)
        with self.assertRaises(ValueError, msg="not found"):
            tracker.execute([lambda etab: None])

    def test_skips_inactive_etablissement(self):
        inactive_etab = EtablissementFactory(active=False)
        called = []

        tracker = TaskTracker("fetch_reviews", inactive_etab.id)
        tracker.execute([lambda etab: called.append(True)])

        self.assertEqual(called, [])
        self.assertIsNone(tracker.task_execution)

    def test_skip_active_check_processes_inactive(self):
        inactive_etab = EtablissementFactory(active=False)
        called = []

        tracker = TaskTracker("fetch_reviews", inactive_etab.id, skip_active_check=True)
        tracker.execute([lambda etab: called.append(True)])

        self.assertEqual(called, [True])

    def test_stores_metadata(self):
        tracker = TaskTracker("fetch_reviews", self.etab.id, metadata={"custom": "value"})
        tracker.execute([lambda etab: None])

        tracker.task_execution.refresh_from_db()
        self.assertEqual(tracker.task_execution.metadata["custom"], "value")
        self.assertEqual(tracker.task_execution.metadata["etablissement_id"], self.etab.id)
