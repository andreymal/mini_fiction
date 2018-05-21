#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def run():
    from flask.helpers import get_load_dotenv
    from flask.cli import ScriptInfo, load_dotenv

    from mini_fiction.management import manager

    manager.populate_commands()

    # Необходимо создать приложение заранее для загрузки команд из плагинов
    if get_load_dotenv(manager.cli.load_dotenv):
        load_dotenv()
    obj = ScriptInfo(create_app=manager.cli.create_app)
    obj.load_app()

    return manager.cli(obj=obj)


if __name__ == "__main__":
    run()
