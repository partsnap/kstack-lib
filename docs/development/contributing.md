# Contributing

Guide for contributing to kstack-lib.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/partsnap/kstack-lib.git
   cd kstack-lib
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all unit tests
uv run pytest tests/ -v -m unit

# Run with coverage
uv run pytest tests/ -v -m unit --cov=kstack_lib --cov-report=term

# Run specific test file
uv run pytest tests/test_redis_client.py -v
```

## Code Style

We use ruff for linting and formatting:

```bash
# Check code style
uv run ruff check kstack_lib tests

# Auto-fix issues
uv run ruff check kstack_lib tests --fix

# Format code
uv run ruff format kstack_lib tests
```

## Type Checking

We use mypy for type checking:

```bash
uv run mypy kstack_lib
```

## Documentation

Build and serve documentation locally:

```bash
uv run mkdocs serve
# Visit http://127.0.0.1:8100
```

## Pull Request Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes

3. Run tests and linters:
   ```bash
   uv run pytest tests/ -v -m unit
   uv run ruff check kstack_lib tests
   uv run mypy kstack_lib
   ```

4. Commit with descriptive message:
   ```bash
   git commit -m "Add feature: XYZ"
   ```

5. Push and create PR:
   ```bash
   git push origin feature/my-feature
   ```

## Code Guidelines

- Write unit tests for all new features
- Maintain >80% test coverage
- Add docstrings to all public functions/classes
- Follow existing code style and patterns
- Update documentation for API changes

## Testing Guidelines

- Use `@pytest.mark.unit` for unit tests
- Mock external dependencies (Redis, Kubernetes, etc.)
- Test both sync and async code paths
- Test error handling and edge cases
