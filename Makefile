
ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGES = analyticsdataserver analytics_data_api
DATABASES = default analytics

.PHONY: requirements develop clean diff.report view.diff.report quality syncdb

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
	. ./.test_env && ./manage.py test --settings=analyticsdataserver.settings.test \
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
	pep8 --config=.pep8 $(PACKAGES)
	pylint --rcfile=.pylintrc $(PACKAGES)

	# Ignore module level docstrings and all test files
	#pep257 --ignore=D100,D203 --match='(?!test).*py' $(PACKAGES)

validate: test.requirements test quality

syncdb:
	$(foreach db_name,$(DATABASES),./manage.py syncdb --migrate --noinput --database=$(db_name);)

loaddata: syncdb
	python manage.py loaddata courses education_levels single_course_activity course_enrollment_birth_year course_enrollment_education course_enrollment_gender problem_response_answer_distribution course_enrollment_daily countries course_enrollment_country --database=analytics

demo: clean requirements loaddata
	python manage.py set_api_key edx edx
