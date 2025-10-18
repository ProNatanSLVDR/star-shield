from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict, NotRequired
from django_components import component


class HeaderConfig(TypedDict, total=False):
    """Configuration for a table header column."""
    label: str
    key: str
    orderable: bool
    searchable: bool
    icon: Optional[str]
    centered: bool
    popover_if_long: bool
    popover_threshold: int


class CellData(TypedDict, total=False):
    """Data for a single table cell."""
    type: str
    value: Any
    variant: str
    tooltip: Optional[str]
    sort_value: Optional[Any]
    centered: Union[bool, str]
    popover_if_long: bool
    popover_threshold: int
    is_long: NotRequired[bool]
    buttons: NotRequired[List[Dict[str, Any]]]


def normalize_header(header: Union[str, Dict[str, Any]]) -> HeaderConfig:
    """Convert header input to normalized HeaderConfig.
    
    Args:
        header: Either a string (label) or dict with header properties
        
    Returns:
        Normalized HeaderConfig dictionary
    """
    if isinstance(header, dict):
        return {
            "label": header.get("label", header.get("key", "")),
            "key": header.get("key", header.get("label", "").lower().replace(" ", "_")),
            "orderable": header.get("orderable", False),
            "searchable": header.get("searchable", False),
            "icon": header.get("icon", None),
            "centered": header.get("centered", False),
            "popover_if_long": header.get("popover_if_long", False),
            "popover_threshold": header.get("popover_threshold", 15),
        }
    
    # String header
    return {
        "label": header,
        "key": header.lower().replace(" ", "_"),
        "orderable": False,
        "searchable": False,
        "icon": None,
        "centered": False,
        "popover_if_long": False,
        "popover_threshold": 15,
    }


def check_text_is_long(text: str, threshold: int, popover_enabled: bool) -> bool:
    """Determine if text exceeds popover threshold.
    
    Args:
        text: Text to check
        threshold: Character threshold for display
        popover_enabled: Whether popover is enabled for this cell
        
    Returns:
        True if text length exceeds threshold and popover is enabled
    """
    if not popover_enabled:
        return False
    
    try:
        return len(text.strip()) > int(threshold)
    except (ValueError, TypeError):
        return False


def process_cell(
    cell_data: Any, 
    header: HeaderConfig
) -> CellData:
    """Convert raw cell data to processed CellData.
    
    Args:
        cell_data: Raw cell data from row
        header: Header configuration for this cell
        
    Returns:
        Processed CellData dictionary
    """
    if isinstance(cell_data, dict):
        cell_type = cell_data.get("type", "text")
        
        if cell_type == "badge":
            return {
                "type": "badge",
                "value": cell_data.get("value", ""),
                "variant": cell_data.get("variant", "secondary"),
                "tooltip": cell_data.get("tooltip", None),
                "sort_value": cell_data.get("sort_value", None),
                "centered": header["centered"],
                "popover_if_long": header["popover_if_long"],
                "popover_threshold": header["popover_threshold"],
            }
        
        if cell_type == "buttons":
            return {
                "type": "buttons",
                "buttons": cell_data.get("buttons", []),
                "tooltip": cell_data.get("tooltip", None),
                "centered": header["centered"],
                "popover_if_long": header["popover_if_long"],
                "popover_threshold": header["popover_threshold"],
            }
        
        if cell_type == "html":
            return {
                "type": "html",
                "value": cell_data.get("value", ""),
                "tooltip": cell_data.get("tooltip", None),
                "centered": header["centered"],
                "popover_if_long": header["popover_if_long"],
                "popover_threshold": header["popover_threshold"],
            }
        
        # Default dict handling (assume text with metadata)
        value_str = str(cell_data.get("value", "")) if cell_data.get("value") is not None else ""
        return {
            "type": "text",
            "value": value_str,
            "tooltip": cell_data.get("tooltip", None),
            "sort_value": cell_data.get("sort_value", None),
            "centered": header["centered"],
            "popover_if_long": header["popover_if_long"],
            "popover_threshold": header["popover_threshold"],
            "is_long": check_text_is_long(value_str, header["popover_threshold"], header["popover_if_long"]),
        }
    
    # Scalar value
    value_str = "" if cell_data is None else str(cell_data)
    return {
        "type": "text",
        "value": value_str,
        "tooltip": None,
        "sort_value": None,
        "centered": header["centered"],
        "popover_if_long": header["popover_if_long"],
        "popover_threshold": header["popover_threshold"],
        "is_long": check_text_is_long(value_str, header["popover_threshold"], header["popover_if_long"]),
    }


def process_row(
    row: Dict[str, Any], 
    headers: List[HeaderConfig]
) -> Dict[str, Any]:
    """Convert raw row data to processed row with cells.
    
    Args:
        row: Raw row data
        headers: Processed headers for column mapping
        
    Returns:
        Processed row with cells and metadata
    """
    cells = []
    has_buttons = False
    
    for header in headers:
        cell_data = row.get(header["key"], "")
        processed_cell = process_cell(cell_data, header)
        cells.append(processed_cell)
        
        if processed_cell.get("type") == "buttons":
            has_buttons = True
    
    return {
        "cells": cells,
        "modal_link": row.get("modal_link", None),
        "has_buttons": has_buttons,
    }


@component.register("table")
class Table(component.Component):
    template_name = "table/table.html"

    def get_context_data(
        self,
        headers: Optional[List[Union[str, Dict[str, Any]]]] = None,
        rows: Optional[List[Dict[str, Any]]] = None,
        title: Optional[str] = None,
        modal_size: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Process table data and return context for template.
        
        Args:
            headers: List of header definitions (strings or dicts)
            rows: List of row data (dicts)
            title: Optional table title
            modal_size: Bootstrap modal size ('sm', 'lg', 'xl')
            **kwargs: Additional context variables
            
        Returns:
            Context dictionary for template rendering
        """
        # Normalize all headers
        processed_headers = [normalize_header(h) for h in (headers or [])]
        
        # Track if any column is searchable
        has_searchable = any(h.get("searchable", False) for h in processed_headers)
        
        # Process all rows
        processed_rows = [
            process_row(row, processed_headers) 
            for row in (rows or [])
        ]

        return {
            "headers": processed_headers,
            "rows": processed_rows,
            "title": title,
            "searchable": has_searchable,
            "is_empty": len(processed_rows) == 0,
            "modal_size": modal_size,
            **kwargs,
        }
