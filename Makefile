
ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGES = analyticsdataserver analytics_data_api
DATABASES = default analytics

.PHONY: requirements develop clean diff.report view.diff.report quality

requirements:
	pip install -q -r requirements/base.txt

test.requirements: requirements
	pip install -q -r requirements/test.txt

develop: test.requirements
	pip install -q -r requirements/local.txt

clean:
	find . -name '*.pyc' -delete
	coverage erase

test: clean
	. ./.test_env && ./manage.py test --settings=analyticsdataserver.settings.test --with-ignore-docstrings \
		--exclude-dir=analyticsdataserver/settings --with-coverage --cover-inclusive --cover-branches \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		$(foreach package,$(PACKAGES),--cover-package=$(package)) \
		$(PACKAGES)

diff.report:
	diff-cover $(COVERAGE)/coverage.xml --html-report $(COVERAGE)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(COVERAGE)/diff_quality_pep8.html
	diff-quality --violations=pylint --html-report $(COVERAGE)/diff_quality_pylint.html

view.diff.report:
	xdg-open file:///$(COVERAGE)/diff_cover.html
	xdg-open file:///$(COVERAGE)/diff_quality_pep8.html
	xdg-open file:///$(COVERAGE)/diff_quality_pylint.html

quality:
	pep8 $(PACKAGES)
	pylint $(PACKAGES)

	# Ignore module level docstrings and all test files
	#pep257 --ignore=D100,D203 --match='(?!test).*py' $(PACKAGES)

validate: test.requirements test quality

migrate:
	$(foreach db_name,$(DATABASES),./manage.py migrate --noinput --database=$(db_name);)

loaddata: migrate
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data

demo: clean requirements loaddata
	python manage.py set_api_key edx edx

travis: clean requirements migrate
	python manage.py set_api_key edx edx
	python manage.py loaddata problem_response_answer_distribution --database=analytics
	python manage.py generate_fake_course_data --num-weeks=1
