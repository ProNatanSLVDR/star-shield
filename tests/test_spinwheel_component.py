from unittest.mock import MagicMock

from django.test import SimpleTestCase

from components.spinwheel.spinwheel import SpinWheel


class TestNormalizePrize(SimpleTestCase):
    def setUp(self):
        self.component = SpinWheel("spinwheel")

    def test_normalizes_dict_prize(self):
        prize = {"name": "Free Coffee", "icon": "fa-coffee", "id": 1}
        result = self.component._normalize_prize(prize)
        self.assertEqual(result["name"], "Free Coffee")
        self.assertEqual(result["icon"], "fa-coffee")
        self.assertEqual(result["id"], 1)

    def test_normalizes_dict_with_defaults(self):
        prize = {"id": 2}
        result = self.component._normalize_prize(prize)
        self.assertEqual(result["icon"], "fa-solid fa-gift")
        self.assertEqual(result["id"], 2)

    def test_normalizes_object_prize(self):
        prize = MagicMock()
        prize.name = "Discount"
        prize.icon = "fa-percent"
        prize.id = 3
        result = self.component._normalize_prize(prize)
        self.assertEqual(result["name"], "Discount")
        self.assertEqual(result["icon"], "fa-percent")
        self.assertEqual(result["id"], 3)

    def test_normalizes_object_with_defaults(self):
        prize = MagicMock(spec=[])  # No attributes
        result = self.component._normalize_prize(prize)
        self.assertEqual(result["icon"], "fa-solid fa-gift")
        self.assertIsNone(result["id"])


class TestResolveStopIndex(SimpleTestCase):
    def setUp(self):
        self.component = SpinWheel("spinwheel")
        self.prizes = [
            {"id": 1, "name": "Coffee"},
            {"id": 2, "name": "Tea"},
            {"id": 3, "name": "Nothing"},
        ]

    def test_returns_none_for_none_stop_on(self):
        result = self.component._resolve_stop_index(self.prizes, None)
        self.assertIsNone(result)

    def test_resolves_by_valid_index(self):
        result = self.component._resolve_stop_index(self.prizes, 1)
        self.assertEqual(result, 1)

    def test_resolves_int_as_id_when_out_of_range(self):
        result = self.component._resolve_stop_index(self.prizes, 99)
        self.assertIsNone(result)

    def test_resolves_int_matching_prize_id(self):
        result = self.component._resolve_stop_index(self.prizes, 3)
        # 3 is a valid index range (0-2), so it returns index 3? No, len is 3, so 3 >= 3
        # Falls through to id matching: prize with id=3 is at index 2
        self.assertEqual(result, 2)

    def test_resolves_by_name_string(self):
        result = self.component._resolve_stop_index(self.prizes, "Tea")
        self.assertEqual(result, 1)

    def test_resolves_by_name_case_insensitive(self):
        result = self.component._resolve_stop_index(self.prizes, "tea")
        self.assertEqual(result, 1)

    def test_resolves_by_object_with_id(self):
        obj = MagicMock()
        obj.id = 2
        obj.name = "Tea"
        result = self.component._resolve_stop_index(self.prizes, obj)
        self.assertEqual(result, 1)

    def test_resolves_by_object_with_name(self):
        obj = MagicMock(spec=["name"])
        obj.id = None
        obj.name = "Nothing"
        result = self.component._resolve_stop_index(self.prizes, obj)
        self.assertEqual(result, 2)

    def test_returns_none_for_unmatched_string(self):
        result = self.component._resolve_stop_index(self.prizes, "Unknown")
        self.assertIsNone(result)

    def test_returns_none_for_unmatched_object(self):
        obj = MagicMock()
        obj.id = 999
        obj.name = "Unknown"
        result = self.component._resolve_stop_index(self.prizes, obj)
        self.assertIsNone(result)
