
COVERAGE = build/coverage

PACKAGE = api
PROJECT_NAME = django-edx-report-data

validate: test quality

test:
	SECRET_KEY=test ./manage.py test --settings=api.settings.test \
		--with-coverage --cover-erase --cover-inclusive \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		--cover-package=api.reportdata --verbosity=2

diff.report:
	diff-cover $(COVERAGE)/coverage.xml --html-report $(COVERAGE)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(COVERAGE)/diff_quality_pep8.html $(PACKAGE)
	diff-quality --violations=pylint --html-report $(COVERAGE)/diff_quality_pylint.html $(PACKAGE)

view.diff.report:
	xdg-open file:///$(COVERAGE)/diff_cover.html
	xdg-open file:///$(COVERAGE)/diff_quality_pep8.html
	xdg-open file:///$(COVERAGE)/diff_quality_pylint.html

quality:
	pep8 --config=.pep8 $(PACKAGE)
	pylint --rcfile=.pylintrc $(PACKAGE)
