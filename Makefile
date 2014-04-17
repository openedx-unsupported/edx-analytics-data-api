
PIP_INSTALL = pip install --use-wheel --find-links=$$WHEEL_URL/Python-$$WHEEL_PYVER

.PHONY:	requirements test test-requirements .tox

uninstall:
	while pip uninstall -y edx.analytics.tasks; do true; done
	python setup.py clean

install: requirements uninstall
	python setup.py install

develop: requirements
	python setup.py develop

system-requirements:
	sudo apt-get update -q
	sudo apt-get install -y -q libmysqlclient-dev

requirements:
	$(PIP_INSTALL) -r requirements/default.txt

test-requirements: requirements
	$(PIP_INSTALL) -r requirements/test.txt

test: test-requirements
	# TODO: when we have better coverage, modify this to actually fail when coverage is too low.
	rm -rf .coverage
	python -m coverage run --rcfile=./.coveragerc -m nose -A 'not acceptance'

test-acceptance: test-requirements
	python -m coverage run --rcfile=./.coveragerc -m nose --nocapture -A acceptance

coverage: test
	python -m coverage html
	python -m coverage xml -o coverage.xml
	diff-cover coverage.xml --html-report diff_cover.html

	# Compute quality
	diff-quality --violations=pep8 --html-report diff_quality_pep8.html
	diff-quality --violations=pylint --html-report diff_quality_pylint.html

	# Compute style violations
	pep8 edx > pep8.report || echo "Not pep8 clean"
	pylint -f parseable edx > pylint.report || echo "Not pylint clean"

jenkins: .tox
	virtualenv ./venv
	./venv/bin/pip install -U tox
	./venv/bin/tox -v --recreate

get_config = $(shell echo "$$ACCEPTANCE_TEST_CONFIG" | python -c 'import sys, json; print json.load(sys.stdin)[sys.argv[1]]' $(1))
VENV_ROOT = $(shell echo "$$WORKSPACE/build/venvs")
META_BIN = $(VENV_ROOT)/meta/bin
EXPORTER_BIN = $(VENV_ROOT)/analytics-exporter/bin
export EXPORTER=$(EXPORTER_BIN)/exporter
TASKS_BIN = $(VENV_ROOT)/analytics-tasks/bin
export REMOTE_TASK=$(TASKS_BIN)/remote-task

jenkins-acceptance:
	mkdir -p $(VENV_ROOT)

	virtualenv $(VENV_ROOT)/analytics-tasks
	virtualenv $(VENV_ROOT)/analytics-exporter
	virtualenv $(VENV_ROOT)/meta

	$(META_BIN)/pip install awscli
	$(META_BIN)/aws s3 rm --recursive $(call get_config,tasks_output_url)$(call get_config,identifier) || true

	$(EXPORTER_BIN)/$(PIP_INSTALL) -r $$WORKSPACE/analytics-exporter/requirements.txt
	$(EXPORTER_BIN)/$(PIP_INSTALL) -e $$WORKSPACE/analytics-exporter/

	. $(TASKS_BIN)/activate && $(MAKE) test-acceptance
