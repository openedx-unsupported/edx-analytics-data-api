.PHONY:	requirements test test-requirements

install: requirements
	python setup.py install

develop: requirements
	python setup.py develop

requirements:
	pip install -r requirements/default.txt

test-requirements: requirements
	pip install -r requirements/test.txt

test: test-requirements
	# TODO: when we have better coverage, modify this to actually fail when coverage is too low.
	rm -rf .coverage
	python -m coverage run --rcfile=./.coveragerc `which nosetests`

coverage: test
	coverage html
	coverage xml -o coverage.xml
	diff-cover coverage.xml --html-report diff_cover.html

	# Compute quality
	diff-quality --violations=pep8 --html-report diff_quality_pep8.html
	diff-quality --violations=pylint --html-report diff_quality_pylint.html

	# Compute style violations
	pep8 > pep8.report || echo "Not pep8 clean"
	pylint -f parseable edx > pylint.report || echo "Not pylint clean"
