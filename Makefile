.PHONY: seed transform app dev test docs clean

PYTHON = .venv/bin/python
DBT    = .venv/bin/dbt
PYTEST = .venv/bin/pytest

seed:
	$(PYTHON) data_gen/generate_loans.py
	$(PYTHON) data_gen/generate_payments.py
	$(PYTHON) data_gen/generate_platforms.py
	$(PYTHON) data_gen/generate_spv.py
	$(PYTHON) data_gen/seed_snowflake.py

transform:
	cd dbt_loanlens && $(CURDIR)/$(DBT) deps --profiles-dir . && \
	$(CURDIR)/$(DBT) run --profiles-dir . && \
	$(CURDIR)/$(DBT) test --profiles-dir .

app:
	.venv/bin/streamlit run app/main.py

dev: seed transform app

test:
	$(PYTEST) tests/ -v
	cd dbt_loanlens && $(CURDIR)/$(DBT) test --profiles-dir .

docs:
	cd dbt_loanlens && $(CURDIR)/$(DBT) docs generate --profiles-dir . && \
	$(CURDIR)/$(DBT) docs serve --profiles-dir .

clean:
	find . -name "*.pyc" -delete
	rm -rf dbt_loanlens/target dbt_loanlens/dbt_packages
