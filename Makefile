
ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
PACKAGES = analyticsdata analyticsdataclient

validate: test.requirements test quality

test.requirements:
	pip install -q -r requirements/test.txt

clean:
	find . -name '*.pyc' -delete
	coverage erase

test.app: clean
	. ./.test_env && ./manage.py test --settings=analyticsdataserver.settings.test \
		--with-coverage --cover-inclusive --cover-branches \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		--cover-package=analyticsdata \
		analyticsdata/

test.client:
	nosetests --with-coverage --cover-inclusive --cover-branches \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		--cover-package=analyticsdataclient \
		analyticsdataclient/

test: test.requirements test.app test.client

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
	pep257 --ignore=D100 --match='(?!test).*py' $(PACKAGES)
