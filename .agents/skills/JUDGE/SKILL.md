```markdown
# JUDGE Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the JUDGE repository, a Python codebase with no detected framework. You'll learn how to structure files, write imports and exports, follow commit message conventions, and understand the project's testing approach. This guide is designed to help you contribute effectively and maintain consistency across the codebase.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `user_manager.py`, `data_loader.py`

### Imports
- Use **relative imports** within the project.
  - Example:
    ```python
    from .utils import parse_input
    from .models import JudgeResult
    ```

### Exports
- Use **named exports** (explicitly listing what is exported from a module).
  - Example:
    ```python
    __all__ = ['Judge', 'JudgeResult']
    ```

### Commit Messages
- **Freeform** style, no strict prefixes.
- Average commit message length: ~57 characters.
- Example:
  ```
  Add validation for user input in judge module
  ```

## Workflows

### Adding a New Module
**Trigger:** When you need to add new functionality.
**Command:** `/add-module`

1. Create a new Python file using snake_case (e.g., `new_feature.py`).
2. Implement your logic using relative imports for dependencies.
3. Add named exports to the module using `__all__`.
4. Write or update tests as appropriate.
5. Commit your changes with a clear, descriptive message.

### Updating an Existing Module
**Trigger:** When modifying or refactoring existing code.
**Command:** `/update-module`

1. Locate the relevant Python file.
2. Make your changes, ensuring all imports remain relative.
3. Update `__all__` if you add or remove exports.
4. Run or update tests to cover your changes.
5. Commit with a descriptive message.

### Writing Tests
**Trigger:** When adding or updating functionality.
**Command:** `/write-test`

1. Create or update test files following the `*.test.ts` pattern (note: TypeScript test pattern detected; ensure Python compatibility or clarify test approach).
2. Write tests covering the new or changed logic.
3. Run tests to verify correctness.

## Testing Patterns

- **Framework:** Unknown (no Python testing framework detected).
- **File Pattern:** Tests are named with the `*.test.ts` pattern, which is typical for TypeScript, not Python. If using Python, consider adopting a standard like `test_*.py` and a framework such as `pytest` or `unittest`.
- **Example Test File Name:** `judge.test.ts` (if using TypeScript) or `test_judge.py` (recommended for Python).

## Commands
| Command        | Purpose                                      |
|----------------|----------------------------------------------|
| /add-module    | Scaffold and implement a new Python module   |
| /update-module | Modify or refactor an existing module        |
| /write-test    | Add or update tests for your code            |
```
