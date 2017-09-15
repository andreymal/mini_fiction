.PHONY: all

help:
	@echo "mini_fiction"
	@echo
	@echo "clean - remove all build, test, coverage, frontend and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with pylint"
	@echo "test - run tests quickly with the default Python with pytest"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python and pytest"
	@echo "release - package and upload a release"
	@echo "release-sign - package and upload a release with PGP sign"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "develop - install the package for development as editable"
	@echo "babel-extract - create messages.pot translation template"
	@echo "babel-update - update .po translation files"
	@echo "babel-compile - compile .po translation files to .mo"

clean: clean-build clean-pyc clean-translations

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr .tox/
	rm -fr *.egg-info
	rm -fr *.egg

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-translations:
	rm -f mini_fiction/translations/*/LC_MESSAGES/*.mo

lint:
	python3 setup.py lint \
	--lint-packages mini_fiction \
	--lint-rcfile pylintrc

test:
	pybabel compile -d mini_fiction/translations
	python3 setup.py test

test-all:
	pybabel compile -d mini_fiction/translations
	tox

coverage:
	pip3 install -r test-requirements.txt
	py.test --cov=mini_fiction --cov-report=html tests
	ls -lh htmlcov/index.html

release: clean
	python3 setup.py sdist upload
	pybabel compile -d mini_fiction/translations
	python3 setup.py bdist_wheel upload

release-sign: clean
	python3 setup.py sdist upload --sign
	pybabel compile -d mini_fiction/translations
	python3 setup.py bdist_wheel upload --sign

dist: clean
	python3 setup.py sdist
	pybabel compile -d mini_fiction/translations
	python3 setup.py bdist_wheel
	ls -lh dist

install: clean
	python3 setup.py install

develop:
	pip3 install -r requirements.txt
	pip3 install -r dev-requirements.txt
	pip3 install -r test-requirements.txt
	python3 setup.py develop
	pybabel compile -d mini_fiction/translations

babel-extract:
	pybabel extract \
		-F babel.cfg \
		-k lazy_gettext \
		-o messages.pot \
		--project mini_fiction \
		--copyright-holder andreymal \
		--version 0.0.2 \
		--msgid-bugs-address andriyano-31@mail.ru \
		mini_fiction

babel-update: babel-extract
	pybabel update -i messages.pot -d mini_fiction/translations

babel-compile:
	pybabel compile -d mini_fiction/translations
