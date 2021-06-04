.PHONY: help clean clean-build clean-pyc clean-translations clean-frontend lint test test-all coverage release release-test release-sign release-sign-test dist install develop babel-extract babel-update babel-compile frontend frontend-build

PYTHON?=python3
PIP?=pip3
FIND?=find
NPM?=npm

help:
	@echo "mini_fiction"
	@echo
	@echo "clean - remove all build, test, coverage, frontend and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-translations - remove gettext *.mo files"
	@echo "clean-frontend - remove frontend build"
	@echo "lint - check style with pylint"
	@echo "format - reformat with black"
	@echo "test - run tests quickly with the default Python with pytest"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python and pytest"
	@echo "release - package and upload a release to PyPI using twine"
	@echo "release-test - package and upload a release to TestPyPI using twine"
	@echo "release-sign - package, sign and upload a release to PyPI using twine"
	@echo "release-sign-test - package, sign and upload a release to TestPyPI using twine"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "develop - install the package for development as editable"
	@echo "babel-extract - create messages.pot translation template"
	@echo "babel-update - update .po translation files"
	@echo "babel-compile - compile .po translation files to .mo"
	@echo "frontend - build development bundle"
	@echo "frontend-build - build production bundle"

clean: clean-build clean-pyc clean-translations clean-frontend

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr .tox/
	rm -fr *.egg-info
	rm -fr *.egg

clean-pyc:
	$(FIND) . -name '*.pyc' -exec rm -f {} +
	$(FIND) . -name '*.pyo' -exec rm -f {} +
	$(FIND) . -name '*~' -exec rm -f {} +
	$(FIND) . -name '__pycache__' -exec rm -fr {} +

clean-translations:
	rm -f mini_fiction/translations/*/LC_MESSAGES/*.mo

clean-frontend:
	rm -f mini_fiction/frontend/build/*

lint:
	pylint --rcfile=pylintrc mini_fiction/logic
	mypy mini_fiction/logic
	flake8 mini_fiction/logic

format:
	isort mini_fiction/logic
	black mini_fiction/logic

test:
	pybabel compile -d mini_fiction/translations
	$(PYTHON) setup.py test

test-all:
	pybabel compile -d mini_fiction/translations
	tox

coverage:
	$(PIP) install -r test-requirements.txt
	py.test --cov=mini_fiction --cov-report=html --cov-branch tests
	ls -lh htmlcov/index.html

release: dist
	twine upload dist/*

release-test: dist
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

release-sign: dist
	twine upload --sign --sign-with gpg dist/*

release-sign-test: dist
	twine upload --sign --sign-with gpg --repository-url https://test.pypi.org/legacy/ dist/*

dist: clean
	$(PYTHON) setup.py sdist
	pybabel compile -d mini_fiction/translations
	cd mini_fiction/frontend && $(NPM) run-script build
	$(PYTHON) setup.py bdist_wheel
	ls -lh dist

install: clean
	$(PYTHON) setup.py install

develop:
	$(PIP) install -r requirements.txt -r optional-requirements.txt -r dev-requirements.txt -r test-requirements.txt
	$(PIP) install -e .
	pybabel compile -d mini_fiction/translations
	cd mini_fiction/frontend && $(NPM) install
	cd mini_fiction/frontend && $(NPM) run-script webpack
	ln -s ../frontend/build mini_fiction/static/ --force

babel-extract:
	pybabel extract \
		-F babel.cfg \
		-k lazy_gettext \
		-o messages.pot \
		--project mini_fiction \
		--copyright-holder andreymal \
		--version 0.0.4 \
		--msgid-bugs-address andriyano-31@mail.ru \
		mini_fiction

babel-update: babel-extract
	pybabel update -i messages.pot -d mini_fiction/translations

babel-compile:
	pybabel compile -d mini_fiction/translations

frontend:
	cd mini_fiction/frontend && $(NPM) run-script webpack

frontend-build:
	cd mini_fiction/frontend && $(NPM) run-script build
