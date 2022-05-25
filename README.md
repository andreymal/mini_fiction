# mini_fiction

[![frontend](https://github.com/andreymal/mini_fiction/actions/workflows/frontend-workflow.yml/badge.svg)](https://github.com/andreymal/mini_fiction/actions/workflows/frontend-workflow.yml)
[![backend-lint](https://github.com/andreymal/mini_fiction/actions/workflows/backend-lint.yml/badge.svg)](https://github.com/andreymal/mini_fiction/actions/workflows/backend-lint.yml)

Library CMS on Python for fanfics

## Features

* fanfics with genres, characters and events
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

Install [lxml]. Then:

```bash
pip install mini_fiction
mkdir media
mini_fiction seed
mini_fiction createsuperuser
mini_fiction run
```

CMS will be available at `http://localhost:5000/`, administration page is `http://localhost:5000/admin/`.

Flask uses production environment by default. If you want to use a development server, create `.env` file in your
working directory and put some settings here:

```dotenv
FLASK_ENV=development
```

You can override this file using native environment variables (example for bash):

```bash
export FLASK_ENV=production
mini_fiction run
```

## Configuration

Just copy `local_settings.example.py` to `local_settings.py` and edit it.
Then run `mini_fiction run` in the same directory with this file: settings will be loaded automatically.
Ensure that `MINIFICTION_SETTINGS` is **not** used in `.env` file.

Alternatively you can put `MINIFICTION_SETTINGS=local_settings.Local` to `.env` file if you think that explicit is
better than implicit.

If mini_fiction can't import module `local_settings`, try to set environment variable `PYTHONPATH=.`
Don't forget `export PYTHONPATH` for unix shells.

If you want to change domain (e.g. `127.0.0.1:5000` or `example.com` instead of default `localhost:5000`),
change `SERVER_NAME` option.

You can run `mini_fiction status` to check some configuration variables.

## Next steps

Don't forget to change the `SECRET_KEY` option before using mini_fiction on production!

Search, avatars and captcha are disabled by default.

For more information see `INSTALL.md` (in Russian).

[Manticore]: https://manticoresearch.com/

[lxml]: https://lxml.de/installation.html
