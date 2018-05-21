#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pkgutil
import importlib

import click
from flask.cli import FlaskGroup

from mini_fiction import application


commands_populated = False


def populate_commands():
    global commands_populated
    if commands_populated:
        return

    from flask.cli import run_command, routes_command

    from mini_fiction.management import commands as commands_module

    # Загружаем стандартные команды Flask
    cli.add_command(run_command)
    cli.add_command(routes_command)
    # shell_command у нас свой

    # Загружаем наши собственные команды
    for _, modname, _ in pkgutil.iter_modules(commands_module.__path__):
        importlib.import_module('mini_fiction.management.commands.' + modname)

    # Плагины заботятся о загрузке команд сами при инициализации себя
    commands_populated = True


@click.group(cls=FlaskGroup, add_default_commands=False, create_app=application.create_app)
def cli():
    pass
