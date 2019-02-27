#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name,unused-variable

import pytest
from pony import orm

from mini_fiction import models


def test_get_tags_objects_existing_strings(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()
    tag3 = factories.TagFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1.name, tag3.name, tag2.name])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, tag3, tag2]  # Порядок должен сохраняться
    assert tags_info['aliases'] == []
    assert tags_info['blacklisted'] == []
    assert tags_info['invalid'] == []
    assert tags_info['created'] == []
    assert tags_info['nonexisting'] == []


def test_get_tags_objects_existing_tagobjects(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()
    tag3 = factories.TagFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, tag3, tag2])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, tag3, tag2]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_existing_mixed(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()
    tag3 = factories.TagFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, tag3.iname, tag2])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, tag3, tag2]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_existing_duplicated(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag2, tag1.iname + ' ', tag2.iname, tag1])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag2, tag1, tag2, tag1]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []



def test_get_tags_objects_aliases_enabled_tagobj(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = models.Tag.bl.get_tags_objects([tag1_alias])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1]
    assert tags_info['aliases'] == [tag1_alias]
    for k in ('blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_aliases_enabled_string(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = models.Tag.bl.get_tags_objects(['просто_тег'])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1]
    assert tags_info['aliases'] == [tag1_alias]
    for k in ('blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_aliases_disabled(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = models.Tag.bl.get_tags_objects(['просто_тег'], resolve_aliases=False)

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1_alias]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_blacklist_enabled(app, factories):
    tag1 = factories.TagFactory()
    bad_tag = factories.TagFactory(name='Ужасный тег', reason_to_blacklist='Потому что ужасный')

    tags_info = models.Tag.bl.get_tags_objects([tag1.name, 'ужасный тег'])

    assert tags_info['success'] is False
    assert tags_info['tags'] == [tag1, None]
    assert tags_info['blacklisted'] == [bad_tag]
    for k in ('aliases', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_blacklist_disabled(app, factories):
    tag1 = factories.TagFactory()
    bad_tag = factories.TagFactory(name='Ужасный тег', reason_to_blacklist='Потому что ужасный')

    tags_info = models.Tag.bl.get_tags_objects([tag1.name, 'ужасный тег'], resolve_blacklisted=False)

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, bad_tag]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_nonexisting_create(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, 'Новый \nтег '], create=True, user=user)

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is not None
    assert new_tag.name == 'Новый тег'
    assert new_tag.created_by == user

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, new_tag]
    assert tags_info['created'] == [new_tag]
    for k in ('aliases', 'blacklisted', 'invalid', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_nonexisting_create_duplicated(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, 'Новый \nтег ', 'новЫй     ТЕГ    '], create=True, user=user)

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is not None
    assert new_tag.name == 'Новый тег'
    assert new_tag.created_by == user

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, new_tag, new_tag]
    assert tags_info['created'] == [new_tag]
    for k in ('aliases', 'blacklisted', 'invalid', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_nonexisting_create_invalid(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, 'Новый \nтег ', '×', ' '], create=True, user=user)

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is None  # При любой ошибке теги не создаются
    assert models.Tag.get(name='×') is None

    assert tags_info['success'] is False
    assert tags_info['tags'] == [tag1, None, None, None]
    assert tags_info['invalid'][0][0] == '×'
    assert tags_info['invalid'][1][0] == ' '
    for k in ('aliases', 'blacklisted', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_nonexisting_create_without_user(app, factories):
    tag1 = factories.TagFactory()

    with pytest.raises(ValueError) as excinfo:
        models.Tag.bl.get_tags_objects([tag1, 'Новый \nтег '], create=True)
    assert str(excinfo.value) == 'Not authenticated'

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is None


def test_get_tags_objects_nonexisting_nocreate(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = models.Tag.bl.get_tags_objects([tag1, 'Новый \nтег '], create=False, user=user)

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is None

    assert tags_info['success'] is False
    assert tags_info['tags'] == [tag1, None]
    assert tags_info['nonexisting'] == ['Новый \nтег ']
    for k in ('aliases', 'blacklisted', 'created', 'invalid'):
        assert tags_info[k] == []
