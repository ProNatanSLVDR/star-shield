from django_components import component

@component.register("table")
class Table(component.Component):
    template_name = "table/table.html"

    def get_context_data(self, headers=None, rows=None, title=None, modal_size=None, **kwargs):
        # Process headers to ensure they have label, key, orderable, searchable flags and icon
        processed_headers = []
        has_searchable = False
        for header in headers or []:
            if isinstance(header, dict):
                processed_headers.append({
                    'label': header.get('label', header.get('key', '')),
                    'key': header.get('key', header.get('label', '').lower().replace(' ', '_')),
                    'orderable': header.get('orderable', False),
                    'searchable': header.get('searchable', False),
                    'icon': header.get('icon', None),
                    'centered': header.get('centered', False),
                    'popover_if_long': header.get('popover_if_long', False),
                    'popover_threshold': header.get('popover_threshold', 15),
                })
                if header.get('searchable', False):
                    has_searchable = True
            else:
                processed_headers.append({
                    'label': header,
                    'key': header.lower().replace(' ', '_'),
                    'orderable': False,
                    'searchable': False,
                    'icon': None,
                    'centered': False,
                    'popover_if_long': False,
                    'popover_threshold': 15,
                })

        # Process rows to use header keys and handle tooltips and modal links
        processed_rows = []
        for row_index, row in enumerate(rows or []):
            processed_cells = []
            has_buttons = False
            for header in processed_headers:
                cell_data = row.get(header['key'], '')
                if isinstance(cell_data, dict):
                    # Handle badge data
                    if cell_data.get('type') == 'badge':
                        processed_cells.append({
                            'type': 'badge',
                            'value': cell_data.get('value', ''),
                            'variant': cell_data.get('variant', 'secondary'),
                            'tooltip': cell_data.get('tooltip', None),
                            'sort_value': cell_data.get('sort_value', None),
                            'centered': header['centered'],
                            'popover_if_long': header['popover_if_long'],
                            'popover_threshold': header['popover_threshold'],
                        })
                    # Handle button data
                    elif cell_data.get('type') == 'buttons':
                        has_buttons = True           
                        processed_cells.append({
                            'type': 'buttons',
                            'buttons': cell_data.get('buttons', []),
                            'tooltip': cell_data.get('tooltip', None),
                            'centered': header['centered'],
                            'popover_if_long': header['popover_if_long'],
                            'popover_threshold': header['popover_threshold'],
                        })
                    elif cell_data.get('type') == 'html':
                        processed_cells.append({
                            'type': 'html',
                            'value': cell_data.get('value', ''),
                            'tooltip': cell_data.get('tooltip', None),
                            'centered': header['centered'],
                            'popover_if_long': header['popover_if_long'],
                            'popover_threshold': header['popover_threshold'],
                        })
                    else:
                        value_str = cell_data.get('value', '')
                        if value_str is None:
                            value_str = ''
                        value_str = str(value_str)
                        value_for_length = value_str.strip()
                        is_long = False
                        try:
                            is_long = bool(header['popover_if_long'] and len(value_for_length) > int(header['popover_threshold']))
                        except Exception:
                            is_long = False

                        processed_cells.append({
                            'type': 'text',
                            'value': value_str,
                            'tooltip': cell_data.get('tooltip', None),
                            'sort_value': cell_data.get('sort_value', None),
                            'centered': header['centered'],
                            'popover_if_long': header['popover_if_long'],
                            'popover_threshold': header['popover_threshold'],
                            'is_long': is_long,
                        })
                else:
                    value_str = '' if cell_data is None else str(cell_data)
                    value_for_length = value_str.strip()
                    is_long = False
                    try:
                        is_long = bool(header['popover_if_long'] and len(value_for_length) > int(header['popover_threshold']))
                    except Exception:
                        is_long = False

                    processed_cells.append({
                        'type': 'text',
                        'value': value_str,
                        'tooltip': None,
                        'sort_value': None,
                        'centered': header['centered'],
                        'popover_if_long': header['popover_if_long'],
                        'popover_threshold': header['popover_threshold'],
                        'is_long': is_long,
                    })
            
            # Add modal link if present
            modal_link = row.get('modal_link', None)
            
            processed_rows.append({
                'cells': processed_cells,
                'modal_link': modal_link,
                'has_buttons': has_buttons
            })

        return {
            "headers": processed_headers,
            "rows": processed_rows,
            "title": title,
            "searchable": has_searchable,
            "is_empty": len(processed_rows) == 0,
            "modal_size": modal_size,
            **kwargs
        }
