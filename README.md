# mini_fiction

[![frontend](https://github.com/andreymal/mini_fiction/actions/workflows/frontend-workflow.yml/badge.svg)](https://github.com/andreymal/mini_fiction/actions/workflows/frontend-workflow.yml)
[![backend-lint](https://github.com/andreymal/mini_fiction/actions/workflows/backend-lint.yml/badge.svg)](https://github.com/andreymal/mini_fiction/actions/workflows/backend-lint.yml)

Library CMS on Python for fanfics

## Features

* fanfics with characters and tags
* comments with trees
* search (powered by [Manticore])
* user profiles with contacts
* pre-moderation of fanfics
* favorites and bookmarks
* notices from administrator
* PJAX-like loading of page content
* customizable design
* primitive plugin system

CMS currently in Russian, and we would be grateful for the translation of all phrases in English.

## Quick start

mini_fiction is available on PyPI, but it's recommended to use the latest version from GitHub since it's
more up-to-date. Install Python 3.8-3.11 and the development tools ([Git], GNU Make, [Poetry], [Node.js]
and [Yarn]), then run the following commands to set up the development environment:

```bash
git clone https://github.com/andreymal/mini_fiction
cd mini_fiction
make develop
```

This project is managed by Poetry; use `poetry shell` the activate the virtual environment.

Then:

```bash
mkdir media
mini_fiction seed
mini_fiction createsuperuser
mini_fiction run
```

CMS will be available at `http://localhost:5000/`, administration page is `http://localhost:5000/admin/`.

Use `mini_fiction --debug run` to enable the reloader and debugger (see the Flask documentation for details).

Use `make dist` to create a `.whl` file for use in production.

## Configuration

Just copy `local_settings.example.py` to `local_settings.py` and edit it.
Then run `mini_fiction run` in the same directory with this file: settings will be loaded automatically.

If mini_fiction can't import the `local_settings` module, try to set environment variable `PYTHONPATH=.`
Don't forget `export PYTHONPATH` for unix shells.

You can use the `MINIFICTION_SETTINGS` environment variable to load another settings module, for example
`MINIFICTION_SETTINGS=my_settings.SuperProd`.

If you want to change domain (e.g. `127.0.0.1:5000` or `example.com` instead of default `localhost:5000`),
change the `SERVER_NAME` option.

You can run `mini_fiction status` to check some configuration variables.

## Next steps

Don't forget to change the `SECRET_KEY` option before using mini_fiction on production!

Search and captcha are disabled by default.

For more information see `INSTALL.md` (in Russian).

[Manticore]: https://manticoresearch.com/

[Git]: https://git-scm.com/

[Poetry]: https://python-poetry.org/

[Node.js]: https://nodejs.org/en

[Yarn]: https://yarnpkg.com/
