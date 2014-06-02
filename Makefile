
ROOT = $(shell echo "$$PWD")
COVERAGE = $(ROOT)/build/coverage
DJANGO_ROOT = service

validate: test quality

test:
	find . -name '*.pyc' -delete
	SECRET_KEY=test ./manage.py test --settings=service.settings.test \
		--with-coverage --cover-erase --cover-inclusive \
		--cover-html --cover-html-dir=$(COVERAGE)/html/ \
		--cover-xml --cover-xml-file=$(COVERAGE)/coverage.xml \
		--cover-package=analyticsdata

diff.report:
	diff-cover $(COVERAGE)/coverage.xml --html-report $(COVERAGE)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(COVERAGE)/diff_quality_pep8.html
	diff-quality --violations=pylint --html-report $(COVERAGE)/diff_quality_pylint.html

view.diff.report:
	xdg-open file:///$(COVERAGE)/diff_cover.html
	xdg-open file:///$(COVERAGE)/diff_quality_pep8.html
	xdg-open file:///$(COVERAGE)/diff_quality_pylint.html

quality:
	pep8 --config=.pep8
	pylint --rcfile=.pylintrc $(DJANGO_ROOT)
