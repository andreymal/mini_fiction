import pytest

from mini_fiction.logic import tags
from mini_fiction import models
from mini_fiction.validation import ValidationError


def test_get_tags_objects_existing_strings(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()
    tag3 = factories.TagFactory()

    tags_info = tags.get_tags_objects([tag1.name, tag3.name, tag2.name])

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

    tags_info = tags.get_tags_objects([tag1, tag3, tag2])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, tag3, tag2]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_existing_mixed(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()
    tag3 = factories.TagFactory()

    tags_info = tags.get_tags_objects([tag1, tag3.iname, tag2])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1, tag3, tag2]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_existing_duplicated(app, factories):
    tag1 = factories.TagFactory()
    tag2 = factories.TagFactory()

    tags_info = tags.get_tags_objects([tag2, tag1.iname + ' ', tag2.iname, tag1])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag2, tag1, tag2, tag1]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []



def test_get_tags_objects_aliases_enabled_tagobj(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = tags.get_tags_objects([tag1_alias])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1]
    assert tags_info['aliases'] == [tag1_alias]
    for k in ('blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_aliases_enabled_string(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = tags.get_tags_objects(['просто_тег'])

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1]
    assert tags_info['aliases'] == [tag1_alias]
    for k in ('blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_aliases_disabled(app, factories):
    tag1 = factories.TagFactory()
    tag1_alias = factories.TagFactory(name='Просто тег', is_alias_for=tag1)

    tags_info = tags.get_tags_objects(['просто_тег'], resolve_aliases=False)

    assert tags_info['success'] is True
    assert tags_info['tags'] == [tag1_alias]
    for k in ('aliases', 'blacklisted', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_blacklist_enabled(app, factories):
    tag1 = factories.TagFactory()
    bad_tag = factories.TagFactory(name='Ужасный тег', reason_to_blacklist='Потому что ужасный')

    tags_info = tags.get_tags_objects([tag1.name, 'ужасный тег'])

    assert tags_info['success'] is False
    assert tags_info['tags'] == [tag1, None]
    assert tags_info['blacklisted'] == [bad_tag]
    for k in ('aliases', 'invalid', 'created', 'nonexisting'):
        assert tags_info[k] == []


def test_get_tags_objects_nonexisting_create(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = tags.get_tags_objects([tag1, 'Новый \nтег '], should_create=True, user=user)

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

    tags_info = tags.get_tags_objects([tag1, 'Новый \nтег ', 'новЫй     ТЕГ    '], should_create=True, user=user)

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

    tags_info = tags.get_tags_objects([tag1, 'Новый \nтег ', '×', ' '], should_create=True, user=user)

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
        tags.get_tags_objects([tag1, 'Новый \nтег '], should_create=True)
    assert str(excinfo.value) == 'Not authenticated'

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is None


def test_get_tags_objects_nonexisting_nocreate(app, factories):
    tag1 = factories.TagFactory()
    user = factories.AuthorFactory()

    tags_info = tags.get_tags_objects([tag1, 'Новый \nтег '], should_create=False, user=user)

    new_tag = models.Tag.get(iname='новый_тег')
    assert new_tag is None

    assert tags_info['success'] is False
    assert tags_info['tags'] == [tag1, None]
    assert tags_info['nonexisting'] == ['Новый \nтег ']
    for k in ('aliases', 'blacklisted', 'created', 'invalid'):
        assert tags_info[k] == []


def test_tag_create_normal(factories):
    admin = factories.AuthorFactory(is_staff=True)

    tag = tags.create(admin, {
        'name': 'Тестовый тег',
        'category': None,
        'color': None,
        'description': 'Это описание тега',
    })

    assert tag.name == 'Тестовый тег'
    assert tag.iname == 'тестовый_тег'
    assert tag.category is None
    assert tag.description == 'Это описание тега'
    assert tag.is_spoiler is False
    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''


def test_tag_create_noadmin(factories):
    admin = factories.AuthorFactory(is_staff=False)
    old_tags_count = models.Tag.select().count()

    with pytest.raises(ValueError) as excinfo:
        tags.create(admin, {'name': 'Тестовый тег'})

    assert str(excinfo.value) == 'Not authorized'
    assert models.Tag.select().count() == old_tags_count
    assert models.Tag.get(iname='тестовый_тег') is None


def test_tag_create_fail_conflict(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(name='Старый тег')
    old_tags_count = models.Tag.select().count()

    with pytest.raises(ValueError) as excinfo:
        tags.create(admin, {'name': ' СтАРЫй  \nТеГ '})

    assert str(excinfo.value.errors['name'][0]) == 'Тег уже существует'
    assert models.Tag.select().count() == old_tags_count
    assert tag.name == 'Старый тег'


def test_tag_create_fail_invalid(factories):
    admin = factories.AuthorFactory(is_staff=True)
    old_tags_count = models.Tag.select().count()

    with pytest.raises(ValueError) as excinfo:
        tags.create(admin, {'name': '×××'})

    assert str(excinfo.value.errors['name'][0]) == 'Пустой тег'
    assert models.Tag.select().count() == old_tags_count



def test_tag_create_alias_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)
    canonical_tag = factories.TagFactory(name='Существующий тег')

    tag = tags.create(admin, {
        'name': 'Тестовый тег',
        'is_alias_for': canonical_tag.name,
    })

    assert tag.iname == 'тестовый_тег'
    assert tag.is_alias is True
    assert tag.is_alias_for == canonical_tag
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''


def test_tag_create_alias_fail_nonexisting(factories):
    admin = factories.AuthorFactory(is_staff=True)
    old_tags_count = models.Tag.select().count()

    with pytest.raises(ValidationError) as excinfo:
        tags.create(admin, {
            'name': 'Тестовый тег',
            'is_alias_for': 'dssdfdsfdhskjsdhcyuierchefvdg',
        })

    assert str(excinfo.value.errors['is_alias_for'][0]) == 'Тег не найден'

    assert models.Tag.select().count() == old_tags_count
    assert models.Tag.get(iname='тестовый_тег') is None


def test_tag_create_blacklist_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)

    tag = tags.create(admin, {
        'name': 'Тестовый тег',
        'reason_to_blacklist': 'Плохой тег',
    })

    assert tag.iname == 'тестовый_тег'
    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is True
    assert tag.reason_to_blacklist == 'Плохой тег'


def test_tag_create_with_category_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)
    category = factories.TagCategoryFactory()

    tag = tags.create(admin, {
        'name': 'Тестовый тег',
        'category': category.id,
    })

    assert tag.iname == 'тестовый_тег'
    assert tag.category == category


def test_tag_create_with_category_fail_nonexisting(factories):
    admin = factories.AuthorFactory(is_staff=True)
    old_tags_count = models.Tag.select().count()

    with pytest.raises(ValidationError) as excinfo:
        tags.create(admin, {
            'name': 'Тестовый тег',
            'category': 345345345,
        })

    assert str(excinfo.value.errors['category'][0]) == 'Недопустимое значение 345345345'

    assert models.Tag.select().count() == old_tags_count
    assert models.Tag.get(iname='тестовый_тег') is None


def test_tag_update_normal(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory()

    tags.update(tag, admin, {
        'name': 'Обновлённый тег',
        'color': '#ff0000',
        'description': 'Это новое описание тега',
    })

    assert tag.name == 'Обновлённый тег'
    assert tag.iname == 'обновлённый_тег'
    assert tag.category is None
    assert tag.description == 'Это новое описание тега'
    assert tag.is_spoiler is False
    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''


def test_tag_update_noadmin(factories):
    admin = factories.AuthorFactory(is_staff=False)
    tag = factories.TagFactory()

    with pytest.raises(ValueError) as excinfo:
        tags.update(tag, admin, {'name': 'Тестовый тег'})


def test_tag_update_fail_conflict(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(name='Старый тег')
    tag2 = factories.TagFactory(name='Существующий тег')

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)
    assert tag.stories_count == 1

    with pytest.raises(ValidationError) as excinfo:
        tags.update(tag, admin, {
            'name': 'СущестВУЮЩиЙ\n тег ',
        })

    assert str(excinfo.value.errors['name'][0]) == 'Тег уже существует'
    assert tag.name == 'Старый тег'
    assert tag.iname == 'старый_тег'
    assert tag.stories_count == 1


def test_tag_update_fail_invalid(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(name='Старый тег')

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)

    with pytest.raises(ValidationError) as excinfo:
        tags.update(tag, admin, {
            'name': '× ×',
        })

    assert str(excinfo.value.errors['name'][0]) == 'Пустой тег'
    assert tag.name == 'Старый тег'
    assert tag.iname == 'старый_тег'


def test_tag_update_alias_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(is_alias_for=None)
    canonical_tag = factories.TagFactory(name='Существующий тег', stories_count=0)

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)
    assert tag.stories_count == 1

    tags.update(tag, admin, {
        'is_alias_for': canonical_tag.name,
    })

    assert tag.is_alias is True
    assert tag.is_alias_for == canonical_tag
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''

    story_tags = set(x.tag for x in story.bl.get_tags_list())
    assert story_tags == {canonical_tag}
    assert tag.stories_count == 0
    assert canonical_tag.stories_count == 1


def test_tag_update_alias_ok_when_story_already_contains_tag(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(is_alias_for=None)
    canonical_tag = factories.TagFactory(name='Существующий тег')
    tag3 = factories.TagFactory(is_alias_for=None)

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)
    story.bl.add_tag(admin, canonical_tag, log=False)
    story.bl.add_tag(admin, tag3, log=False)
    assert tag.stories_count == 1
    assert canonical_tag.stories_count == 1
    assert tag3.stories_count == 1

    tags.update(tag, admin, {
        'is_alias_for': canonical_tag.name,
    })

    assert tag.is_alias is True
    assert tag.is_alias_for == canonical_tag
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''

    story_tags = set(x.tag for x in story.bl.get_tags_list())
    assert story_tags == {canonical_tag, tag3}
    assert tag.stories_count == 0
    assert canonical_tag.stories_count == 1
    assert tag3.stories_count == 1


def test_tag_update_alias_fail_nonexisting(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(is_alias_for=None)
    canonical_tag = factories.TagFactory(name='Существующий тег')

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)

    with pytest.raises(ValidationError) as excinfo:
        tags.update(tag, admin, {
            'is_alias_for': 'dssdfdsfdhskjsdhcyuierchefvdg',
        })

    assert str(excinfo.value.errors['is_alias_for'][0]) == 'Тег не найден'
    assert tag.is_alias is False
    assert tag.is_alias_for is None

    story_tags = set(x.tag for x in story.bl.get_tags_list())
    assert story_tags == {tag}


def test_tag_update_alias_fail_self_reference(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(is_alias_for=None)
    canonical_tag = factories.TagFactory(name='Существующий тег')

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)

    with pytest.raises(ValidationError) as excinfo:
        tags.update(tag, admin, {
            'is_alias_for': tag.name,
        })

    assert str(excinfo.value.errors['is_alias_for'][0]) == 'Тег не может ссылаться сам на себя'
    assert tag.is_alias is False
    assert tag.is_alias_for is None

    story_tags = set(x.tag for x in story.bl.get_tags_list())
    assert story_tags == {tag}


def test_tag_update_alias_fail_self_reference_through_another_alias(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(name='Главный тег', is_alias_for=None)
    tag_alias = factories.TagFactory(name='Синоним тега', is_alias_for=tag)

    with pytest.raises(ValidationError) as excinfo:
        tags.update(tag, admin, {
            'is_alias_for': tag_alias.name,
        })

    assert str(excinfo.value.errors['is_alias_for'][0]) == 'Тег не может ссылаться сам на себя'
    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag_alias.is_alias is True
    assert tag_alias.is_alias_for == tag


def test_tag_update_alias_remove_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)
    canonical_tag = factories.TagFactory(name='Существующий тег')
    tag = factories.TagFactory(is_alias_for=canonical_tag)

    tags.update(tag, admin, {
        'is_alias_for': None,
        'is_hidden_alias': True,
    })

    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''


def test_tag_update_blacklist_ok(factories):
    admin = factories.AuthorFactory(is_staff=True)
    tag = factories.TagFactory(is_alias_for=None)
    tag2 = factories.TagFactory(is_alias_for=None)

    story = factories.StoryFactory()
    story.bl.add_tag(admin, tag, log=False)
    story.bl.add_tag(admin, tag2, log=False)
    assert tag.stories_count == 1
    assert tag2.stories_count == 1

    tags.update(tag, admin, {
        'reason_to_blacklist': 'Плохой тег',
    })

    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is True
    assert tag.reason_to_blacklist == 'Плохой тег'

    story_tags = set(x.tag for x in story.bl.get_tags_list())
    assert story_tags == {tag2}
    assert tag.stories_count == 0
    assert tag2.stories_count == 1


def test_tag_update_alias_to_blacklist(factories):
    admin = factories.AuthorFactory(is_staff=True)
    canonical_tag = factories.TagFactory(name='Существующий тег')
    tag = factories.TagFactory(is_alias_for=canonical_tag)

    tags.update(tag, admin, {
        'reason_to_blacklist': 'Синоним тоже так себе',
    })

    assert tag.is_alias is False
    assert tag.is_alias_for is None
    assert tag.is_hidden_alias is False
    assert tag.is_blacklisted is True
    assert tag.reason_to_blacklist == 'Синоним тоже так себе'


def test_tag_update_alias_to_hidden(factories):
    admin = factories.AuthorFactory(is_staff=True)
    canonical_tag = factories.TagFactory(name='Существующий тег')
    tag = factories.TagFactory(is_alias_for=canonical_tag, is_hidden_alias=False)

    tags.update(tag, admin, {
        'is_hidden_alias': True,
    })

    assert tag.is_alias is True
    assert tag.is_alias_for == canonical_tag
    assert tag.is_hidden_alias is True
    assert tag.is_blacklisted is False
    assert tag.reason_to_blacklist == ''
