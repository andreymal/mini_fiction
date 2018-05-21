============
mini_fiction
============

.. image:: https://api.travis-ci.org/andreymal/mini_fiction.png
    :target: https://travis-ci.org/andreymal/mini_fiction
    :alt: Build Status

Library CMS on Python for fanfics. Currently in development.

Short feature list: fanfics with genres, characters and events; comments
with trees; search (using `Sphinx <http://sphinxsearch.com/>`_); user profiles
with contacts; premoderation of fanfics; favorites and bookmarks; notices
from administrator; PJAX-like loading of page content; customizable design;
primitive plugin system.

CMS currently in Russian, and we would be grateful for the translation
of all phrases in English.


Quick start
-----------

`Install lxml <http://lxml.de/installation.html>`_. Then:

.. code::

    pip install mini_fiction
    mkdir media
    mini_fiction seed
    mini_fiction createsuperuser
    mini_fiction run

Website will be available at ``http://localhost:5000/``, administration page is
``http://localhost:5000/admin/``.

Flask uses production environment by default. If you want to use
a development server, create ``.env`` file in your working directory and put
some settings here:

.. code::

    FLASK_ENV=development

You can override this file using native environment variables:

.. code::

    FLASK_ENV=production mini_fiction run


Configuration file
------------------

Just copy ``local_settings.example.py`` to ``local_settings.py`` and edit it.
Then run ``mini_fiction run`` in the same directory with this file: settings
will be loaded automatically. Ensure that ``MINIFICTION_SETTINGS`` is not used
in ``.env`` file. Alternatively you can put
``MINIFICTION_SETTINGS=local_settings.Local`` to ``.env`` file if you think
that explicit is better than implicit.

If mini_fiction can't import module ``local_settings``, try to set environment
variable ``PYTHONPATH=.`` (don't forget ``export PYTHONPATH`` for unix
shells).

If you want to change domain (e.g. ``127.0.0.1:5000`` or ``example.com``
instead of default ``localhost:5000``), change ``SERVER_NAME`` option.

You can run ``mini_fiction status`` to check some configuration variables.

Don't forget to change the ``SECRET_KEY`` option before using mini_fiction
on production!

Search, avatars and captcha are disabled by default.

For more information see ``INSTALL.md`` (in Russian).
