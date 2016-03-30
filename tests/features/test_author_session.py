#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

from flask import url_for

from mini_fiction.database import db


def test_author_login_ok(app, client, selenium, live_server, factories):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element_by_name('username').send_keys(author.username)
    selenium.find_element_by_name('password').send_keys('123456')
    selenium.find_element_by_css_selector('.login-form .btn').click()

    assert (
        selenium.find_element_by_id('nav-main')
        .find_element_by_link_text('Выход')
    ) is not None


def test_author_login_nopassword(app, client, selenium, live_server, factories):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element_by_name('username').send_keys(author.username)
    selenium.find_element_by_name('password').send_keys('hackyou')
    selenium.find_element_by_css_selector('.login-form .btn').click()

    page = selenium.find_element_by_css_selector('.row.login-page').text
    assert 'Пожалуйста, введите правильные имя пользователя и пароль' in page


def test_author_login_nocase(app, client, selenium, live_server, factories):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element_by_name('username').send_keys(author.username.upper())
    selenium.find_element_by_name('password').send_keys('123456')
    selenium.find_element_by_css_selector('.login-form .btn').click()

    page = selenium.find_element_by_css_selector('.row.login-page').text
    assert 'Пожалуйста, введите правильные имя пользователя и пароль' in page
