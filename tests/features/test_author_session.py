#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

from flask import url_for
from selenium.webdriver.common.by import By

from mini_fiction.database import db


def test_author_login_ok(app, client, selenium, live_server, factories, wait_ajax):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element(By.LINK_TEXT, 'Войти').click()
    selenium.find_element(By.NAME, 'username').send_keys(author.username)
    selenium.find_element(By.NAME, 'password').send_keys('123456')
    selenium.find_element(By.CSS_SELECTOR, '.controls .btn.btn-primary').click()
    wait_ajax()

    assert author.username in selenium.find_element(By.CSS_SELECTOR, '.nav-main .nav-username').text


def test_author_login_nopassword(app, client, selenium, live_server, factories, wait_ajax):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element(By.LINK_TEXT, 'Войти').click()
    selenium.find_element(By.NAME, 'username').send_keys(author.username)
    selenium.find_element(By.NAME, 'password').send_keys('hackyou')
    selenium.find_element(By.CSS_SELECTOR, '.controls .btn.btn-primary').click()
    wait_ajax()

    page = selenium.find_element(By.CSS_SELECTOR, 'form input[name="username"] + .help-inline').text
    assert 'Пожалуйста, введите правильные имя пользователя и пароль' in page


def test_author_login_is_case_insensitive(app, client, selenium, live_server, factories, wait_ajax):
    author = factories.AuthorFactory()
    author.bl.set_password('123456')
    db.commit()

    selenium.get(url_for('index.index', _external=True))
    selenium.find_element(By.LINK_TEXT, 'Войти').click()
    selenium.find_element(By.NAME, 'username').send_keys(author.username.upper())
    selenium.find_element(By.NAME, 'password').send_keys('123456')
    selenium.find_element(By.CSS_SELECTOR, '.controls .btn.btn-primary').click()
    wait_ajax()

    assert author.username in selenium.find_element(By.CSS_SELECTOR, '.nav-main .nav-username').text
    assert author.username.upper() not in selenium.find_element(By.CSS_SELECTOR, '.nav-main .nav-username').text
