#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def run():
    from flask.cli import ScriptInfo

    from mini_fiction.management import manager

    manager.populate_commands()
    obj = ScriptInfo(create_app=manager.cli.create_app)
    obj.load_app()  # Необходимо для загрузки команд из плагинов
    return manager.cli(obj=obj)


if __name__ == "__main__":
    run()
