============
mini_fiction
============

.. image:: https://api.travis-ci.org/andreymal/mini_fiction.png
    :target: https://travis-ci.org/andreymal/mini_fiction
    :alt: Build Status

Library CMS on Python for fanfics. Currently in development.

Short feature list: fanfics with genres, characters and events; comments with trees;
search (by Sphinx); user profiles with contacts; moderation of fanfics and comments;
favorites and bookmarks; notices from administrator; PJAX-like loading of page content;
customizable design; primitive plugin system.

CMS currently in Russian, and we would be grateful for the translation of all phrases
in English.


Quick start
-----------

`Install lxml <http://lxml.de/installation.html>`_. Then:

.. code::

    pip install mini_fiction
    mkdir media
    mini_fiction seed
    mini_fiction createsuperuser
    mini_fiction runserver

Website will be available at ``http://localhost:5000/``, administration page is
``http://localhost:5000/admin/``.


Configuration file
------------------

Just copy ``local_settings.example.py`` to ``local_settings.py`` and edit it.
Then run ``mini_fiction runserver`` in the same directory with this file.

If mini_fiction can't import module ``local_settings``, try to set environment
variable ``PYTHONPATH=.`` (don't forget ``export PYTHONPATH`` for unix
shells).

If you want to change domain (e.g. ``127.0.0.1:5000`` or ``example.com``
instead of default ``localhost:5000``), change ``SERVER_NAME`` option.

You can run ``mini_fiction status`` to check some configuration variables.

For more information see ``INSTALL.md`` (in Russian).
