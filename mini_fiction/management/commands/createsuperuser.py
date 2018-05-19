#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from getpass import getpass

from pony.orm import db_session

from mini_fiction.models import Author
from mini_fiction.management.manager import manager


@manager.command
def createsuperuser():
    username = input('Username: ')
    email = input('Email address: ')
    while True:
        password = getpass('Password: ')
        password2 = getpass('Password (again): ')
        if password == password2:
            break
        print('Passwords do not match')

    with db_session:
        Author.bl.create({
            'username': username,
            'email': email,
            'password': password,
            'is_staff': True,
            'is_superuser': True,
        })
        print('Superuser created successfully.')
