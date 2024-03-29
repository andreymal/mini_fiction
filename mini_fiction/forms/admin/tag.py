from flask_babel import lazy_gettext
from wtforms import StringField, TextAreaField, BooleanField

from pony import orm

from mini_fiction.models import TagCategory
from mini_fiction.forms.form import Form
from mini_fiction.forms.fields import LazySelectField


class TagForm(Form):
    attrs_dict = {'class': 'input-xxlarge'}
    attrs_tags_dict = {'class': 'input-xxxlarge', 'autocomplete': 'off'}

    name = StringField(
        'Название',
        render_kw=dict(attrs_dict, maxlength=256),
    )

    category = LazySelectField(
        'Категория',
        choices=lambda: [(0, '-')] + list(orm.select((x.id, x.name) for x in TagCategory)),
        coerce=int,
    )

    description = TextAreaField(
        lazy_gettext('Description'),
        render_kw=attrs_dict,
    )

    is_spoiler = BooleanField(
        'Спойлерный тег',
        render_kw=attrs_dict,
        description='Спойлерные теги скрываются в списке тегов рассказа',
    )

    is_alias_for = StringField(
        'Синоним для',
        render_kw=dict(attrs_tags_dict, maxlength=512),
        description='Впишите название основного тега. На него будет заменён тег-синоним у всех рассказов',
    )

    is_hidden_alias = BooleanField(
        'Скрытый синоним',
        render_kw=attrs_dict,
        description='Не показывать в списке синонимов на странице тега, чтобы не смущать пользователей',
    )

    is_extreme_tag = BooleanField(
        'Экстремальный тег',
        render_kw=attrs_dict,
        description='Этим тегом обозначается что-то совсем жёсткое',
    )

    reason_to_blacklist = StringField(
        'Блокировка тега',
        render_kw=dict(attrs_dict, maxlength=256),
        description='Впишите причину, чтобы заблокировать тег. Тег будет удалён у всех рассказов',
    )
