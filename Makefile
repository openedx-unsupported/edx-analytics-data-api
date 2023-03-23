ROOT = $(shell echo "$$PWD")
COVERAGE_DIR = $(ROOT)/build/coverage
DATABASES = default analytics analytics_v1
.DEFAULT_GOAL := help

TOX=''

ifdef TOXENV
TOX := tox -- #to isolate each tox environment if TOXENV is defined
endif

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@perl -nle'print $& if m{^[\.a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

.PHONY: requirements develop clean diff.report view.diff.report quality static docs

requirements:  ## install base requirements
	pip3 install -q -r requirements/base.txt

production-requirements:  ## install production requirements
	pip3 install -r requirements.txt

test.requirements: requirements  ## install base and test requirements
	pip3 install -q -r requirements/test.txt

tox.requirements:  ## install tox requirements
	pip3 install -q -r requirements/tox.txt

develop: test.requirements  ## install test and dev requirements
	pip3 install -q -r requirements/dev.txt

upgrade:
	pip3 install -q -r requirements/pip_tools.txt
	pip-compile --upgrade --allow-unsafe -o requirements/pip.txt requirements/pip.in
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/doc.txt requirements/doc.in
	pip-compile --upgrade -o requirements/dev.txt requirements/dev.in
	pip-compile --upgrade -o requirements/production.txt requirements/production.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	pip-compile --upgrade -o requirements/tox.txt requirements/tox.in
	pip-compile --upgrade -o requirements/ci.txt requirements/ci.in
	scripts/post-pip-compile.sh \
        requirements/pip_tools.txt \
	    requirements/base.txt \
	    requirements/doc.txt \
	    requirements/dev.txt \
	    requirements/production.txt \
	    requirements/test.txt \
	    requirements/tox.txt \
	    requirements/ci.txt
	## Let tox control the Django version for tests
	grep -e "^django==" requirements/base.txt > requirements/django.txt
	sed '/^[dD]jango==/d' requirements/test.txt > requirements/test.tmp
	mv requirements/test.tmp requirements/test.txt


clean:
	$(TOX)coverage erase
	find . -name '*.pyc' -delete

main.test: clean
	export COVERAGE_DIR=$(COVERAGE_DIR) && \
	$(TOX)pytest --cov-report html --cov-report xml

test: main.test

diff.report: test.requirements  ## Show the diff in quality and coverage
	diff-cover $(COVERAGE_DIR)/coverage.xml --html-report $(COVERAGE_DIR)/diff_cover.html
	diff-quality --violations=pycodestyle --html-report $(COVERAGE_DIR)/diff_quality_pycodestyle.html
	diff-quality --violations=pylint --html-report $(COVERAGE_DIR)/diff_quality_pylint.html

view.diff.report:  ## Show the diff in quality and coverage using xdg
	xdg-open file:///$(COVERAGE_DIR)/diff_cover.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pycodestyle.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pylint.html

run_check_isort:
	$(TOX)isort --check-only --recursive --diff analytics_data_api/ analyticsdataserver/

run_pycodestyle:
	$(TOX)pycodestyle --config=.pycodestyle analytics_data_api analyticsdataserver

run_pylint:
	$(TOX)pylint -j 0 --rcfile=pylintrc analytics_data_api analyticsdataserver

run_isort:
	$(TOX)isort --recursive analytics_data_api/ analyticsdataserver/

quality: run_pylint run_check_isort run_pycodestyle  ## run_pylint, run_check_isort, run_pycodestyle (Installs tox requirements.)

validate: test.requirements test quality  ## Runs make test and make quality. (Installs test requirements.)

static:  ## Runs collectstatic
	python manage.py collectstatic --noinput

migrate:  ## Runs django migrations with syncdb and default database
	./manage.py migrate --noinput --run-syncdb --database=default

migrate-all:  ## Runs migrations on all databases
	$(foreach db_name,$(DATABASES),./manage.py migrate --noinput --run-syncdb --database=$(db_name);)

loaddata: migrate-all  ## Runs migrations and generates fake data
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py loaddata problem_response_answer_distribution_analytics_v1 --database=analytics_v1
	python manage.py generate_fake_course_data --database=analytics
	python manage.py generate_fake_course_data --database=analytics_v1

demo: requirements clean loaddata  ## Runs make clean, requirements, and loaddata, sets api key to edx
	python manage.py set_api_key edx edx

# Target used by edx-analytics-dashboard during its testing.
github_ci: test.requirements clean migrate-all  ## Used by CI for testing
	python manage.py set_api_key edx edx
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py loaddata problem_response_answer_distribution_analytics_v1 --database=analytics_v1
	python manage.py generate_fake_course_data --database=analytics --num-weeks=2 --no-videos --course-id "edX/DemoX/Demo_Course"
	python manage.py generate_fake_course_data --database=analytics_v1 --num-weeks=2 --no-videos --course-id "edX/DemoX/Demo_Course"

docs: tox.requirements
	tox -e docs
