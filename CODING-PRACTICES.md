# Coding Practices

This document outlines the coding practices and conventions used in this project. Following these guidelines helps maintain code quality, readability, and consistency.

## 1. General Principles

- **Clarity and Readability:** Write clear, self-documenting code. Avoid overly complex one-liners.
- **Defensive Programming:** Anticipate and handle potential errors gracefully. Use `try...except` blocks for operations that might fail (e.g., API calls, database queries).
- **Don't Repeat Yourself (DRY):** Reuse code where possible. Create helper functions for common tasks.

## 2. Python & Django Best Practices

- **Custom User Model:** The project uses a custom `User` model. Always refer to it using `django.contrib.auth.get_user_model()` where possible, though direct import is used in this codebase.
- **Type Hinting:** All new functions and methods should have type hints for arguments and return values. This improves code clarity and allows for static analysis.
- **Function-Based Views (FBV):** The project currently uses function-based views. Maintain this style for consistency.
- **Django Forms:** Use Django's `forms.Form` or `forms.ModelForm` for handling user input and validation.
- **Fat Models, Thin Views:** Business logic should be placed in models as methods when it relates directly to the data. Views should primarily handle request/response logic.
- **Django Components:** The project uses `django-components`. Encapsulate reusable UI elements into components.
- **Environment Variables:** Store sensitive information and environment-specific settings in environment variables, accessed via `django.conf.settings`.
- **Logging:** Use Python's `logging` module to log important events, especially errors and warnings.

## 3. Code Style & Formatting

- **PEP 8:** Follow the PEP 8 style guide for Python code.
- **Imports:** Organize imports in the following order:
    1.  Future imports (`from __future__ import ...`)
    2.  Standard library imports
    3.  Third-party library imports
    4.  Local application (Django app) imports
- **Naming Conventions:**
    - `snake_case` for variables, functions, and methods.
    - `PascalCase` for classes.
    - Prefix internal helper functions with an underscore (e.g., `_my_helper_function`).
- **f-strings:** Use f-strings for string formatting.
- **Comments:** Use comments to explain *why* something is done, not *what* is being done. The code should explain the 'what'. Leave `TODO` comments for future work.

## 4. Type Hinting

- Use type hints for all function and method signatures.
- Use modern type hint syntax (e.g., `list[str]` instead of `typing.List[str]`).
- Use `typing.NamedTuple` for defining structured arguments for components.

```python
from django.http import HttpRequest, HttpResponse

def my_view(request: HttpRequest, user_id: int) -> HttpResponse:
    # ... view logic ...
```

## 5. Error Handling & Logging

- Use `try...except` blocks to catch specific exceptions. Avoid bare `except:` clauses.
- When an object is not found in the database, raise `Http404`.
- Log exceptions with relevant context information.

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    try:
        # ... some operation ...
    except ValueError as e:
        logger.error("An error occurred: %s", e)
        # ... handle error ...
```

## 6. Components

- Reusable UI elements are implemented as components using `django-components`.
- Components should have a clear interface defined using `Kwargs` with `NamedTuple`.
- The template for a component is defined in a `template.html` file within the component's directory.

## 7. Internationalization

- Use Django's translation framework for all user-facing strings.
- Use `gettext_lazy` (`_`) for strings in models and forms.
- Use `gettext` (`_`) in views and templates.

```python
from django.utils.translation import gettext_lazy as _
from django.db import models

class MyModel(models.Model):
    name = models.CharField(_("name"), max_length=100)
```

