ROOT = $(shell echo "$$PWD")
COVERAGE_DIR = $(ROOT)/build/coverage
PACKAGES = analyticsdataserver analytics_data_api
DATABASES = default analytics
ELASTICSEARCH_VERSION = 1.5.2
ELASTICSEARCH_PORT = 9223
TEST_SETTINGS = analyticsdataserver.settings.test

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

develop: test.requirements
	pip install -q -r requirements/dev.txt

upgrade: ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -q -r requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/doc.txt requirements/doc.in
	pip-compile --upgrade -o requirements/dev.txt requirements/dev.in
	pip-compile --upgrade -o requirements/production.txt requirements/production.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	scripts/post-pip-compile.sh \
        requirements/pip_tools.txt \
	    requirements/base.txt \
	    requirements/doc.txt \
	    requirements/dev.txt \
	    requirements/production.txt \
	    requirements/test.txt

clean:
	find . -name '*.pyc' -delete
	coverage erase

test: clean
	if [ -e elasticsearch-$(ELASTICSEARCH_VERSION) ]; then curl --silent --head http://localhost:$(ELASTICSEARCH_PORT)/roster_test > /dev/null || make test.run_elasticsearch; fi  # Launch ES if installed and not running
	coverage run ./manage.py test --settings=$(TEST_SETTINGS) \
		--with-ignore-docstrings --exclude-dir=analyticsdataserver/settings \
		$(PACKAGES)
	export COVERAGE_DIR=$(COVERAGE_DIR) && \
		coverage html && \
		coverage xml

diff.report:
	diff-cover $(COVERAGE_DIR)/coverage.xml --html-report $(COVERAGE_DIR)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(COVERAGE_DIR)/diff_quality_pep8.html
	diff-quality --violations=pylint --html-report $(COVERAGE_DIR)/diff_quality_pylint.html

view.diff.report:
	xdg-open file:///$(COVERAGE_DIR)/diff_cover.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pep8.html
	xdg-open file:///$(COVERAGE_DIR)/diff_quality_pylint.html

quality:
	pep8 $(PACKAGES)
	pylint $(PACKAGES)

	# Ignore module level docstrings and all test files
	#pep257 --ignore=D100,D203 --match='(?!test).*py' $(PACKAGES)

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
travis: clean test.requirements migrate
	python manage.py set_api_key edx edx
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data --num-weeks=2 --no-videos --course-id "edX/DemoX/Demo_Course"
