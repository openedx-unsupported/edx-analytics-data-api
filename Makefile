ROOT = $(shell echo "$$PWD")
COVERAGE_DIR = $(ROOT)/build/coverage
DATABASES = default analytics
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

test.run_elasticsearch:
	docker-compose up -d

test.stop_elasticsearch:
	docker-compose stop

test.requirements: requirements  ## install base and test requirements
	pip3 install -q -r requirements/test.txt

tox.requirements:  ## install tox requirements
	pip3 install -q -r requirements/tox.txt

develop: test.requirements  ## install test and dev requirements
	pip3 install -q -r requirements/dev.txt

upgrade: 
	pip3 install -q -r requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/doc.txt requirements/doc.in
	pip-compile --upgrade -o requirements/dev.txt requirements/dev.in
	pip-compile --upgrade -o requirements/production.txt requirements/production.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	pip-compile --upgrade -o requirements/tox.txt requirements/tox.in
	pip-compile --upgrade -o requirements/travis.txt requirements/travis.in
	scripts/post-pip-compile.sh \
        requirements/pip_tools.txt \
	    requirements/base.txt \
	    requirements/doc.txt \
	    requirements/dev.txt \
	    requirements/production.txt \
	    requirements/test.txt \
	    requirements/tox.txt \
	    requirements/travis.txt
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

test:

ifeq ($(DJANGO_SETTINGS_MODULE),analyticsdataserver.settings.devstack)
test: main.test
else
test: test.run_elasticsearch main.test test.stop_elasticsearch
endif

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

loaddata: migrate  ## Runs migrations and generates fake data
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data

create_indices:  ## Create ElasticSearch indices
	python manage.py create_elasticsearch_learners_indices

demo: requirements clean loaddata  ## Runs make clean, requirements, and loaddata, sets api key to edx
	python manage.py set_api_key edx edx

# Target used by edx-analytics-dashboard during its testing.
travis: test.requirements clean migrate-all  ## Used by travis for testing
	python manage.py set_api_key edx edx
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data --num-weeks=2 --no-videos --course-id "edX/DemoX/Demo_Course"

docker_build:
	docker build . -f Dockerfile -t openedx/analytics-data-api
	docker build . -f Dockerfile --target newrelic -t openedx/analytics-data-api:latest-newrelic

travis_docker_tag: docker_build
	docker tag openedx/analytics-data-api openedx/analytics-data-api:$$TRAVIS_COMMIT
	docker tag openedx/analytics-data-api:latest-newrelic openedx/analytics-data-api:$$TRAVIS_COMMIT-newrelic

travis_docker_auth:
	echo "$$DOCKER_PASSWORD" | docker login -u "$$DOCKER_USERNAME" --password-stdin

travis_docker_push: travis_docker_tag travis_docker_auth ## push to docker hub
	docker push 'openedx/analytics-data-api:latest'
	docker push "openedx/analytics-data-api:$$TRAVIS_COMMIT"
	docker push 'openedx/analytics-data-api:latest-newrelic'
	docker push "openedx/analytics-data-api:$$TRAVIS_COMMIT-newrelic"

docs: tox.requirements
	tox -e docs
