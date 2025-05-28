setup: # setup the environment with poetry
	pip install pipx
	pipx install poetry>=2
	poetry install
	poetry run pre-commit install
	poetry env activate

check: # run quality checking tools
	poetry check --lock
	poetry run pre-commit run -a
	poetry run mypy .

test: # test the code with pytest
	poetry run pytest --cov --cov-config=pyproject.toml --cov-report=html tests/

build: # build package
	rm -rf dist/
	poetry build

publish: # publish package to PYPI
	poetry config pypi-token.pypi $(PYPI_TOKEN)
	poetry publish --dry-run
	poetry publish
