# Run from the repository root. No dotenv files are loaded.
PYTHON ?= python3.12
PORT ?= 8000
export DATA_DIR KB_DIR VAR_DIR
MOCK_ENV = env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL

.PHONY: setup rebuild run
setup:
	$(PYTHON) -m venv starter/.venv
	starter/.venv/bin/python -m pip install -r starter/requirements.txt
	npm --prefix frontend ci

rebuild:
	$(MOCK_ENV) $(MAKE) -C starter rebuild
	npm --prefix frontend run build

run:
	@test -f frontend/dist/index.html || (echo 'Run make rebuild first (frontend missing).' >&2; exit 1)
	$(MOCK_ENV) $(MAKE) -C starter run PORT=$(PORT)
