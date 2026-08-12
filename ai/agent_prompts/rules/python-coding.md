# Python Coding Guidelines

## Code Quality
- Write concise, clean, and readable code
- Use type hints for all function signatures and class attributes
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
  - Don't use abbreviations

## Testing
- Practice Test-Driven Development (TDD)
- Write tests before implementing functionality
- Maintain high test coverage
- Use pytest as the testing framework

## Structure
- Keep methods short (≤ 10 lines)
- Keep classes under 150 lines
- Keep files under 150 lines total
- Split large modules into smaller, focused modules

## Pre-commit
- Run pre-commit hooks after completing each task
- Fix all linting and formatting issues before committing
- Ensure all tests pass before committing

## Soft Rules
- Prefer composition over inheritance
- Use early returns to reduce nesting
- Extract repeated logic into expert classes
  - if not possible: extract into helper functions
- Document complex logic with docstrings
  - Be concise and clear when documenting
- Handle errors gracefully

## Work Process
- Understand the codebase before making changes
- Follow existing patterns and conventions
- Test your changes when possible
- Run linting and type checking after modifications
- Never commit changes unless explicitly requested
