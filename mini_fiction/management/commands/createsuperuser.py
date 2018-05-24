#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from getpass import getpass

import click
from pony.orm import db_session, sql_debug

from mini_fiction.models import Author
from mini_fiction.management.manager import cli


@cli.command(short_help='Creates an admin account.', help='Creates an administrator account (is_staff=True and is_superuser=True).')
@click.option('--username', 'username', help='Specifies the login for the superuser.', required=False)
@click.option('--email', 'email', help='Specifies the email for the superuser.', required=False)
@click.option(
    '--noinput', '--no-input', 'noinput',
    help='Tells mini_fiction to NOT prompt the user for input of any kind. '
    'You must use --username with --noinput. Superusers created '
    'with --noinput will not be able to log in until they\'re given '
    'a valid password.',
    is_flag=True,
)
def createsuperuser(username, email, noinput):
    sql_debug(False)

    if not username and noinput:
        print('You must use --username with --noinput.')
        sys.exit(1)

    if not username:
        while True:
            username = input('Username: ')
            if username:
                break
            print('This field cannot be blank.')

    if not email and not noinput:
        email = input('Email address: ')

    if noinput:
        password = ''
    else:
        while True:
            password = getpass('Password: ')
            password2 = getpass('Password (again): ')
            if password == password2:
                break
            del password2
            print('Your passwords didn\'t match.')

    with db_session:
        Author.bl.create({
            'username': username,
            'email': email,
            'password': password,
            'is_staff': True,
            'is_superuser': True,
        })
    print('Superuser created successfully.')
