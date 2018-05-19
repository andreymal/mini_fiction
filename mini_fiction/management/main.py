#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pkgutil
import importlib

from mini_fiction import application


commands_populated = False


def populate_commands():
    global commands_populated
    if commands_populated:
        return

    from mini_fiction.management import commands as commands_module

    for _, modname, _ in pkgutil.iter_modules(commands_module.__path__):
        importlib.import_module('mini_fiction.management.commands.' + modname)

    commands_populated = True



def run():
    from mini_fiction.management.manager import manager

    if manager.app is None:
        manager(application.create_app)

    populate_commands()
    manager.run()


if __name__ == "__main__":
    run()
