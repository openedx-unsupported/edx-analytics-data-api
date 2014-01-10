.PHONY:	requirements test test-requirements

install: requirements
	python setup.py install

develop: requirements
	python setup.py develop

requirements:
	pip install -r requirements/default.txt

test-requirements: requirements
	pip install -r requirements/test.txt
