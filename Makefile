ROOT = $(shell echo "$$PWD")
COVERAGE_DIR = $(ROOT)/build/coverage
PACKAGES = analyticsdataserver analytics_data_api
DATABASES = default analytics
ELASTICSEARCH_VERSION = 1.5.2
ELASTICSEARCH_PORT = 9223
TEST_SETTINGS = analyticsdataserver.settings.test

.PHONY: requirements develop clean diff.report view.diff.report quality

requirements:
	pip install -q -r requirements/base.txt

test.install_elasticsearch:
	curl -L -O https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-$(ELASTICSEARCH_VERSION).zip
	unzip elasticsearch-$(ELASTICSEARCH_VERSION).zip
	echo "http.port: $(ELASTICSEARCH_PORT)" >> elasticsearch-$(ELASTICSEARCH_VERSION)/config/elasticsearch.yml

test.run_elasticsearch:
	cd elasticsearch-$(ELASTICSEARCH_VERSION) && ./bin/elasticsearch -d --http.port=$(ELASTICSEARCH_PORT)

test.requirements: requirements
	pip install -q -r requirements/test.txt

develop: test.requirements
	pip install -q -r requirements/local.txt

clean:
	find . -name '*.pyc' -delete
	coverage erase

test: clean
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

migrate:
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
	python manage.py generate_fake_course_data --num-weeks=1
