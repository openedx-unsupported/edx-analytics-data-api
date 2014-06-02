
REPORTS = build/report
MANAGE = python server/manage.py
PACKAGE_PATHS = django-edx-reports/edx

export SECRET_KEY=testing

validate: test
	pep8 $(PACKAGE_PATHS)
	cd django-edx-reports && pylint --rcfile=../pylintrc edx

runserver:
	$(MANAGE) runserver

install:
	cd django-edx-reports && pip install .

test.requirements: install
	pip install -q -r requirements/local.txt

test.setup:
	rm -rf $(REPORTS)
	mkdir -p $(REPORTS)
	find . -name '*.pyc' -delete

test: test.setup
	$(MANAGE) test --settings=edxapi.settings.test \
		--with-coverage --cover-erase --cover-inclusive \
		--cover-html --cover-html-dir=$(REPORTS)/html/ \
		--cover-xml --cover-xml-file=$(REPORTS)/coverage.xml \
		--cover-package=edx \
		$(PACKAGE_PATHS)

diff.report: test
	diff-cover $(REPORTS)/coverage.xml --html-report $(REPORTS)/diff_cover.html
	diff-quality --violations=pep8 --html-report $(REPORTS)/diff_quality_pep8.html $(PACKAGE_PATHS)
	diff-quality --violations=pylint --html-report $(REPORTS)/diff_quality_pylint.html $(PACKAGE_PATHS)

view.diff.report: diff.report
	xdg-open file:///$$PWD/$(REPORTS)/diff_cover.html
	xdg-open file:///$$PWD/$(REPORTS)/diff_quality_pep8.html
	xdg-open file:///$$PWD/$(REPORTS)/diff_quality_pylint.html
