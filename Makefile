
ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
DJANGO_ROOT = analyticsdataserver
COVER_PACKAGE = analyticsdata

validate: test.requirements test quality

test.requirements:
	pip install -q -r requirements/test.txt

clean:
	find . -name '*.pyc' -delete

test: clean
	. ./.test_env && ./manage.py test --settings=$(DJANGO_ROOT).settings.test \
		--with-coverage --cover-erase --cover-inclusive \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		--cover-package=$(COVER_PACKAGE)

diff.report:
	diff-cover $(COVERAGE)/coverage.xml --html-report $(COVERAGE)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(COVERAGE)/diff_quality_pep8.html
	diff-quality --violations=pylint --html-report $(COVERAGE)/diff_quality_pylint.html

view.diff.report:
	xdg-open file:///$(COVERAGE)/diff_cover.html
	xdg-open file:///$(COVERAGE)/diff_quality_pep8.html
	xdg-open file:///$(COVERAGE)/diff_quality_pylint.html

quality:
	# Excludes settings files
	pep8 --config=.pep8

	# Also excludes settings files. Also modifies the PYTHONPATH to include the DJANGO_ROOT directory.
	pylint --rcfile=.pylintrc $(DJANGO_ROOT)

	# Ignore module level docstrings and all test files
	pep257 --ignore=D100 --match='(!?:test)' $(DJANGO_ROOT)
