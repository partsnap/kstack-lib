tag := $(shell uv pip show kstack-lib | grep Version | awk '{print $$2}')

.PHONY: install
install: ## Install the uv environment
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking uv lock file consistency with 'pyproject.toml': Running uv lock --check"
	@uv lock --check
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Checking for obsolete dependencies: Running dependency check"
	@uv pip check

.PHONY: clean-tox
clean-tox: ## deleting tox directory
	@echo "🚀 Deleting Tox folder"
	@rm -rf .tox

.PHONY: tox
tox: ## running test in tox
	@echo "🚀 Testing code: Running Tox"
	@uv run tox --recreate

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest --cov --cov-config=pyproject.toml --cov-report=xml --ignore=tests/test_cluster_environment.py --ignore=tests/test_local_environment.py

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@uv run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@uv run mkdocs serve

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo tag=$(tag)
.DEFAULT_GOAL := help
