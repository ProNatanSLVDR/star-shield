from __future__ import annotations

from typing import Any

from django.test import SimpleTestCase

from components.table.table import (
    CellData,
    HeaderConfig,
    check_text_is_long,
    normalize_header,
    process_cell,
    process_row,
)


class NormalizeHeaderTests(SimpleTestCase):
    """Test normalize_header function for header standardization."""

    def test_normalize_dict_header_with_all_fields(self) -> None:
        """Test normalizing dict header with all configuration fields."""
        header: dict[str, Any] = {
            "label": "User Name",
            "key": "user_name",
            "orderable": True,
            "searchable": True,
            "icon": "fa-solid fa-user",
            "centered": True,
            "popover_if_long": True,
            "popover_threshold": 25,
        }

        result: HeaderConfig = normalize_header(header)

        self.assertEqual(result["label"], "User Name")
        self.assertEqual(result["key"], "user_name")
        self.assertTrue(result["orderable"])
        self.assertTrue(result["searchable"])
        self.assertEqual(result["icon"], "fa-solid fa-user")
        self.assertTrue(result["centered"])
        self.assertTrue(result["popover_if_long"])
        self.assertEqual(result["popover_threshold"], 25)

    def test_normalize_dict_header_with_minimal_fields(self) -> None:
        """Test normalizing dict header with only required fields."""
        header: dict[str, Any] = {
            "label": "Status",
            "key": "status",
        }

        result: HeaderConfig = normalize_header(header)

        self.assertEqual(result["label"], "Status")
        self.assertEqual(result["key"], "status")
        self.assertFalse(result["orderable"])
        self.assertFalse(result["searchable"])
        self.assertIsNone(result["icon"])
        self.assertFalse(result["centered"])
        self.assertFalse(result["popover_if_long"])
        self.assertEqual(result["popover_threshold"], 15)

    def test_normalize_dict_header_label_fallback_to_key(self) -> None:
        """Test that label falls back to key if label not provided."""
        header: dict[str, Any] = {
            "key": "email",
        }

        result: HeaderConfig = normalize_header(header)

        self.assertEqual(result["label"], "email")
        self.assertEqual(result["key"], "email")

    def test_normalize_string_header(self) -> None:
        """Test normalizing simple string header."""
        result: HeaderConfig = normalize_header("User Email")

        self.assertEqual(result["label"], "User Email")
        self.assertEqual(result["key"], "user_email")
        self.assertFalse(result["orderable"])
        self.assertFalse(result["searchable"])
        self.assertIsNone(result["icon"])
        self.assertFalse(result["centered"])
        self.assertFalse(result["popover_if_long"])
        self.assertEqual(result["popover_threshold"], 15)

    def test_normalize_string_header_with_spaces(self) -> None:
        """Test that string headers with spaces get converted to snake_case."""
        result: HeaderConfig = normalize_header("First Name")

        self.assertEqual(result["label"], "First Name")
        self.assertEqual(result["key"], "first_name")

    def test_normalize_string_header_lowercase_conversion(self) -> None:
        """Test that string headers are converted to lowercase keys."""
        result: HeaderConfig = normalize_header("TOTAL AMOUNT")

        self.assertEqual(result["label"], "TOTAL AMOUNT")
        self.assertEqual(result["key"], "total_amount")

    def test_normalize_dict_header_key_auto_generation_from_label(self) -> None:
        """Test that key is auto-generated from label if key not provided."""
        header: dict[str, Any] = {
            "label": "Product Name",
        }

        result: HeaderConfig = normalize_header(header)

        self.assertEqual(result["label"], "Product Name")
        self.assertEqual(result["key"], "product_name")


class CheckTextIsLongTests(SimpleTestCase):
    """Test check_text_is_long function for popover threshold logic."""

    def test_text_below_threshold_returns_false(self) -> None:
        """Test that text below threshold returns False."""
        result: bool = check_text_is_long("Short", threshold=10, popover_enabled=True)

        self.assertFalse(result)

    def test_text_above_threshold_returns_true(self) -> None:
        """Test that text above threshold returns True when popover enabled."""
        result: bool = check_text_is_long("This is a very long text", threshold=10, popover_enabled=True)

        self.assertTrue(result)

    def test_text_equal_to_threshold_returns_false(self) -> None:
        """Test that text equal to threshold returns False (must be greater than)."""
        result: bool = check_text_is_long("1234567890", threshold=10, popover_enabled=True)

        self.assertFalse(result)

    def test_text_exceeds_threshold_by_one_returns_true(self) -> None:
        """Test that text exceeding threshold by one character returns True."""
        result: bool = check_text_is_long("12345678901", threshold=10, popover_enabled=True)

        self.assertTrue(result)

    def test_popover_disabled_returns_false(self) -> None:
        """Test that long text returns False when popover is disabled."""
        result: bool = check_text_is_long("This is a very long text", threshold=10, popover_enabled=False)

        self.assertFalse(result)

    def test_empty_string_returns_false(self) -> None:
        """Test that empty string returns False."""
        result: bool = check_text_is_long("", threshold=10, popover_enabled=True)

        self.assertFalse(result)

    def test_whitespace_only_string_returns_false(self) -> None:
        """Test that whitespace-only string returns False (gets stripped)."""
        result: bool = check_text_is_long("   ", threshold=10, popover_enabled=True)

        self.assertFalse(result)

    def test_text_with_leading_trailing_whitespace_strips_correctly(self) -> None:
        """Test that leading/trailing whitespace is stripped before checking length."""
        result: bool = check_text_is_long("  This is long text  ", threshold=10, popover_enabled=True)

        self.assertTrue(result)

    def test_invalid_threshold_type_returns_false(self) -> None:
        """Test that invalid threshold type gracefully returns False."""
        result: bool = check_text_is_long("Long text", threshold="invalid", popover_enabled=True)  # type: ignore

        self.assertFalse(result)

    def test_none_text_type_returns_false(self) -> None:
        """Test that None as text gracefully returns False."""
        # This tests defensive programming - the function should handle edge cases
        try:
            result: bool = check_text_is_long(None, threshold=10, popover_enabled=True)  # type: ignore
            self.assertFalse(result)
        except AttributeError:
            # If it raises AttributeError, that's also acceptable behavior for None input
            pass


class ProcessCellTests(SimpleTestCase):
    """Test process_cell function for cell data conversion."""

    def _get_default_header(self) -> HeaderConfig:
        """Helper to get a default header for testing."""
        return {
            "label": "Test",
            "key": "test",
            "orderable": False,
            "searchable": False,
            "icon": None,
            "centered": False,
            "popover_if_long": False,
            "popover_threshold": 15,
        }

    def test_process_simple_string_cell(self) -> None:
        """Test processing simple string cell."""
        header: HeaderConfig = self._get_default_header()

        result: CellData = process_cell("Hello", header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "Hello")
        self.assertIsNone(result["tooltip"])
        self.assertIsNone(result["sort_value"])
        self.assertFalse(result["is_long"])

    def test_process_empty_string_cell(self) -> None:
        """Test processing empty string cell."""
        header: HeaderConfig = self._get_default_header()

        result: CellData = process_cell("", header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "")

    def test_process_none_cell(self) -> None:
        """Test processing None cell value."""
        header: HeaderConfig = self._get_default_header()

        result: CellData = process_cell(None, header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "")

    def test_process_numeric_cell(self) -> None:
        """Test processing numeric cell (converts to string)."""
        header: HeaderConfig = self._get_default_header()

        result: CellData = process_cell(42, header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "42")

    def test_process_badge_cell_complete(self) -> None:
        """Test processing badge cell with all fields."""
        header: HeaderConfig = self._get_default_header()
        cell_data: dict[str, Any] = {
            "type": "badge",
            "value": "Active",
            "variant": "success",
            "tooltip": "User is active",
            "sort_value": 1,
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "badge")
        self.assertEqual(result["value"], "Active")
        self.assertEqual(result["variant"], "success")
        self.assertEqual(result["tooltip"], "User is active")
        self.assertEqual(result["sort_value"], 1)

    def test_process_badge_cell_minimal(self) -> None:
        """Test processing badge cell with minimal fields."""
        header: HeaderConfig = self._get_default_header()
        cell_data: dict[str, Any] = {
            "type": "badge",
            "value": "Pending",
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "badge")
        self.assertEqual(result["value"], "Pending")
        self.assertEqual(result["variant"], "secondary")
        self.assertIsNone(result["tooltip"])
        self.assertIsNone(result["sort_value"])

    def test_process_button_cell(self) -> None:
        """Test processing button cell."""
        header: HeaderConfig = self._get_default_header()
        buttons: list[dict[str, Any]] = [
            {
                "text": "Edit",
                "classes": "btn-sm btn-primary",
                "icon": "fa-solid fa-pen",
            }
        ]
        cell_data: dict[str, Any] = {
            "type": "buttons",
            "buttons": buttons,
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "buttons")
        self.assertEqual(result["buttons"], buttons)
        self.assertEqual(len(result["buttons"]), 1)

    def test_process_html_cell(self) -> None:
        """Test processing HTML cell."""
        header: HeaderConfig = self._get_default_header()
        cell_data: dict[str, Any] = {
            "type": "html",
            "value": "<strong>Bold</strong>",
            "tooltip": "HTML content",
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "html")
        self.assertEqual(result["value"], "<strong>Bold</strong>")
        self.assertEqual(result["tooltip"], "HTML content")

    def test_process_dict_cell_with_value_key(self) -> None:
        """Test processing dict cell with value key (defaults to text type)."""
        header: HeaderConfig = self._get_default_header()
        cell_data: dict[str, Any] = {
            "value": "Description",
            "tooltip": "Full description",
            "sort_value": "D",
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "Description")
        self.assertEqual(result["tooltip"], "Full description")
        self.assertEqual(result["sort_value"], "D")

    def test_process_cell_with_centered_header(self) -> None:
        """Test that cell inherits centered property from header."""
        header: HeaderConfig = self._get_default_header()
        header["centered"] = True

        result: CellData = process_cell("Centered", header)

        self.assertTrue(result["centered"])

    def test_process_cell_with_popover_threshold(self) -> None:
        """Test that long text is detected based on header popover settings."""
        header: HeaderConfig = self._get_default_header()
        header["popover_if_long"] = True
        header["popover_threshold"] = 10

        result: CellData = process_cell("This is a long text that exceeds the threshold", header)

        self.assertTrue(result["is_long"])

    def test_process_cell_missing_value_in_dict(self) -> None:
        """Test that dict cell without value key gets empty string."""
        header: HeaderConfig = self._get_default_header()
        cell_data: dict[str, Any] = {
            "type": "text",
            "tooltip": "No value provided",
        }

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "text")
        self.assertEqual(result["value"], "")


class ProcessRowTests(SimpleTestCase):
    """Test process_row function for complete row processing."""

    def _get_headers(self) -> list[HeaderConfig]:
        """Helper to get default headers for testing."""
        return [
            {
                "label": "Name",
                "key": "name",
                "orderable": False,
                "searchable": False,
                "icon": None,
                "centered": False,
                "popover_if_long": False,
                "popover_threshold": 15,
            },
            {
                "label": "Status",
                "key": "status",
                "orderable": False,
                "searchable": False,
                "icon": None,
                "centered": False,
                "popover_if_long": False,
                "popover_threshold": 15,
            },
        ]

    def test_process_row_with_simple_text_cells(self) -> None:
        """Test processing row with simple text values."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "John Doe",
            "status": "Active",
        }

        result: dict[str, Any] = process_row(row, headers)

        self.assertEqual(len(result["cells"]), 2)
        self.assertEqual(result["cells"][0]["value"], "John Doe")
        self.assertEqual(result["cells"][1]["value"], "Active")
        self.assertFalse(result["has_buttons"])

    def test_process_row_with_mixed_cell_types(self) -> None:
        """Test processing row with different cell types."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "Jane Smith",
            "status": {
                "type": "badge",
                "value": "Inactive",
                "variant": "danger",
            },
        }

        result: dict[str, Any] = process_row(row, headers)

        self.assertEqual(len(result["cells"]), 2)
        self.assertEqual(result["cells"][0]["type"], "text")
        self.assertEqual(result["cells"][1]["type"], "badge")
        self.assertEqual(result["cells"][1]["variant"], "danger")

    def test_process_row_with_button_cell_sets_flag(self) -> None:
        """Test that has_buttons flag is set when buttons cell exists."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "Bob Wilson",
            "status": {
                "type": "buttons",
                "buttons": [{"text": "Delete", "classes": "btn-danger"}],
            },
        }

        result: dict[str, Any] = process_row(row, headers)

        self.assertTrue(result["has_buttons"])
        self.assertEqual(result["cells"][1]["type"], "buttons")

    def test_process_row_with_modal_link(self) -> None:
        """Test that modal_link is preserved in processed row."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "Alice Brown",
            "status": "Pending",
            "modal_link": "/api/user/123/details/",
        }

        result: dict[str, Any] = process_row(row, headers)

        self.assertEqual(result["modal_link"], "/api/user/123/details/")

    def test_process_row_with_missing_column_key(self) -> None:
        """Test row processing when row is missing a key that header expects."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "Charlie Davis",
            # Missing 'status' key
        }

        result: dict[str, Any] = process_row(row, headers)

        self.assertEqual(len(result["cells"]), 2)
        self.assertEqual(result["cells"][0]["value"], "Charlie Davis")
        # Missing key should default to empty string
        self.assertEqual(result["cells"][1]["value"], "")

    def test_process_row_with_extra_columns_in_data(self) -> None:
        """Test that extra columns in row data are ignored."""
        headers: list[HeaderConfig] = self._get_headers()
        row: dict[str, Any] = {
            "name": "Eva Green",
            "status": "Active",
            "extra_field": "Should be ignored",
        }

        result: dict[str, Any] = process_row(row, headers)

        # Should only have cells for defined headers
        self.assertEqual(len(result["cells"]), 2)

    def test_process_row_multiple_button_types_sets_flag_once(self) -> None:
        """Test has_buttons flag is set correctly even with multiple button cells."""
        headers_with_buttons: list[HeaderConfig] = self._get_headers()
        headers_with_buttons.append(
            {
                "label": "Actions",
                "key": "actions",
                "orderable": False,
                "searchable": False,
                "icon": None,
                "centered": True,
                "popover_if_long": False,
                "popover_threshold": 15,
            }
        )

        row: dict[str, Any] = {
            "name": "Frank Miller",
            "status": "Active",
            "actions": {
                "type": "buttons",
                "buttons": [{"text": "Edit", "classes": "btn-primary"}],
            },
        }

        result: dict[str, Any] = process_row(row, headers_with_buttons)

        self.assertTrue(result["has_buttons"])


class TableContextDataEdgeCasesTests(SimpleTestCase):
    """Test edge cases for table component context generation."""

    def test_normalize_header_with_dict_missing_label_uses_key(self) -> None:
        """Test header normalization when label is missing but key is present."""
        header: dict[str, Any] = {"key": "id", "orderable": True}

        result: HeaderConfig = normalize_header(header)

        self.assertEqual(result["label"], "id")
        self.assertEqual(result["key"], "id")
        self.assertTrue(result["orderable"])

    def test_process_cell_badge_missing_value_defaults_empty(self) -> None:
        """Test badge cell defaults to empty string when value is missing."""
        header: HeaderConfig = {
            "label": "Status",
            "key": "status",
            "orderable": False,
            "searchable": False,
            "icon": None,
            "centered": False,
            "popover_if_long": False,
            "popover_threshold": 15,
        }
        cell_data: dict[str, Any] = {"type": "badge"}

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "badge")
        self.assertEqual(result["value"], "")

    def test_process_cell_html_preserves_raw_html(self) -> None:
        """Test that HTML cells preserve raw HTML without escaping."""
        header: HeaderConfig = {
            "label": "Content",
            "key": "content",
            "orderable": False,
            "searchable": False,
            "icon": None,
            "centered": False,
            "popover_if_long": False,
            "popover_threshold": 15,
        }
        html_content: str = "<img src='test.jpg' /> <script>alert('test')</script>"
        cell_data: dict[str, Any] = {"type": "html", "value": html_content}

        result: CellData = process_cell(cell_data, header)

        self.assertEqual(result["type"], "html")
        self.assertEqual(result["value"], html_content)

    def test_process_row_with_numeric_header_key(self) -> None:
        """Test processing row where header key doesn't exist in row."""
        headers: list[HeaderConfig] = [
            {
                "label": "ID",
                "key": "id",
                "orderable": True,
                "searchable": False,
                "icon": None,
                "centered": False,
                "popover_if_long": False,
                "popover_threshold": 15,
            }
        ]
        row: dict[str, Any] = {}

        result: dict[str, Any] = process_row(row, headers)

        self.assertEqual(len(result["cells"]), 1)
        self.assertEqual(result["cells"][0]["value"], "")
