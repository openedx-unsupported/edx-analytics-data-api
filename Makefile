ROOT = $(shell echo "$$PWD")
COVERAGE_DIR = $(ROOT)/build/coverage
PACKAGES = analyticsdataserver analytics_data_api
DATABASES = default analytics
ELASTICSEARCH_VERSION = 1.5.2
ELASTICSEARCH_PORT = 9223
PYTHON_ENV=py35
DJANGO_VERSION=django111

.PHONY: requirements develop clean diff.report view.diff.report quality static

requirements:
	pip install -q -r requirements/base.txt

production-requirements:
	pip install -r requirements.txt

test.install_elasticsearch:
	curl -L -O https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-$(ELASTICSEARCH_VERSION).zip
	unzip elasticsearch-$(ELASTICSEARCH_VERSION).zip
	echo "http.port: $(ELASTICSEARCH_PORT)" >> elasticsearch-$(ELASTICSEARCH_VERSION)/config/elasticsearch.yml

test.run_elasticsearch:
	cd elasticsearch-$(ELASTICSEARCH_VERSION) && ./bin/elasticsearch -d --http.port=$(ELASTICSEARCH_PORT)

test.requirements: requirements
	pip install -q -r requirements/test.txt

tox.requirements:
	 pip install -q -r requirements/tox.txt

develop: test.requirements
	pip install -q -r requirements/dev.txt

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -q -r requirements/pip_tools.txt
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
	# Let tox control the Django version for tests
	grep -e "^django==" requirements/base.txt > requirements/django.txt
	sed '/^[dD]jango==/d' requirements/test.txt > requirements/test.tmp
	mv requirements/test.tmp requirements/test.txt


clean: tox.requirements
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-clean
	find . -name '*.pyc' -delete

test: tox.requirements clean
	if [ -e elasticsearch-$(ELASTICSEARCH_VERSION) ]; then curl --silent --head http://localhost:$(ELASTICSEARCH_PORT)/roster_test > /dev/null || make test.run_elasticsearch; fi  # Launch ES if installed and not running
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-tests
	export COVERAGE_DIR=$(COVERAGE_DIR) && \
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-coverage

diff.report: test.requirements
	diff-cover $(COVERAGE_DIR)/coverage.xml --html-report $(COVERAGE_DIR)/diff_cover.html
	diff-quality --violations=pycodestyle --html-report $(COVERAGE_DIR)/diff_quality_pycodestyle.html
	diff-quality --violations=pylint --html-report $(COVERAGE_DIR)/diff_quality_pylint.html

view.diff.report:
	xdg-open file:///$(COVERAGE_DIR)/diff_cover.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pycodestyle.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pylint.html

run_check_isort: tox.requirements
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-check_isort

run_pycodestyle: tox.requirements
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-pycodestyle

run_pylint: tox.requirements
	tox -e $(PYTHON_ENV)-$(DJANGO_VERSION)-pylint

quality: tox.requirements run_pylint run_pycodestyle

validate: test.requirements test quality

static:
	python manage.py collectstatic --noinput

migrate:
	./manage.py migrate --noinput --run-syncdb --database=default

migrate-all:
	$(foreach db_name,$(DATABASES),./manage.py migrate --noinput --run-syncdb --database=$(db_name);)

loaddata: migrate
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data

demo: clean requirements loaddata
	python manage.py set_api_key edx edx

# Target used by edx-analytics-dashboard during its testing.
travis: clean test.requirements migrate-all
	python manage.py set_api_key edx edx
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data --num-weeks=2 --no-videos --course-id "edX/DemoX/Demo_Course"
