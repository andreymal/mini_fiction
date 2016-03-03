.PHONY: clean-pyc clean-build clean-translations clean lint test test-all docs

help:
	@echo "mini_fiction"
	@echo
	@echo "clean - remove all build, test, coverage, frontend and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with pylint"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "develop - install the package for development as editable"

clean: clean-build clean-pyc clean-translations

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -rf {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-translations:
	rm -f mini_fiction/translations/*/LC_MESSAGES/*.mo

lint:
	python setup.py lint \
	--lint-packages mini_fiction \
	--lint-rcfile pylintrc

release: clean
	python setup.py sdist upload
	pybabel compile -d mini_fiction/translations
	python setup.py bdist_wheel upload

dist: clean
	python setup.py sdist
	pybabel compile -d mini_fiction/translations
	python setup.py bdist_wheel
	ls -lh dist

install: clean
	python setup.py install

develop:
	pip install -r dev-requirements.txt
	python setup.py develop
	pybabel compile -d mini_fiction/translations
