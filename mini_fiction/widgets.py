from html import escape
from itertools import chain

from pony import orm
from flask import url_for
from flask_babel import gettext
from markupsafe import Markup
from wtforms.widgets import Select, Input, TextInput
from wtforms.widgets.core import html_params

from mini_fiction.models import Character


class ButtonWidget(object):
    def __init__(self):
        pass

    def __call__(self, field, text='', **kwargs):
        return '<button %s>%s</button>' % (html_params(**kwargs), text)


class ServiceButtonWidget(Input):
    def __init__(self, *args, **kwargs):
        super().__init__('submit', *args, **kwargs)


# TODO: optimize
class StoriesImgSelect(Select):
    def __init__(self, multiple=False):
        super().__init__(multiple=multiple)

    def __call__(self, field, **kwargs):
        if hasattr(field, 'coerce'):
            value = [field.coerce(x) for x in field.data or ()]
        else:
            value = field.data or []
        output = []
        attrs = dict(kwargs)
        group_container_class = attrs['group_container_class']
        for group, option_sublist in chain(field.choices_groups, []):  # TODO: what is second param `choices`?
            output.append('<span class="%s%s" title="%s">' % (group_container_class, group.id, group.name))
            for option in option_sublist:
                # *option == (id, value)
                output.append(self.render_custom_option(
                    field,
                    value=option[0],
                    label=option[1],
                    selected=option[0] in value,
                    id='{}_{}'.format(field.id, option[0]),
                    **attrs
                ))
            output.append('</span>')
        return '\n'.join(output)

    def get_img_url(self, field, value):
        raise NotImplementedError

    def render_custom_option(self, field, value, label, selected, **kwargs):
        container_attrs = kwargs['container_attrs']
        input_attrs = kwargs['input_attrs']
        img_url = self.get_img_url(field, value)
        img_class = 'ui-selected' if selected else ''
        # NOTE: hardcoded width and height are added to prevent FOOC and will be removed ASAP with this piece of crap
        item_image = '<img width="32" height="32" class="%s" src="%s" alt="%s" title="%s" />' % (img_class, img_url, label, label)
        cb = Input('checkbox' if self.multiple else 'radio')
        rendered_cb = cb(field, id=False, value=value, checked=selected, **input_attrs)
        return '<span %s>%s%s</span>' % (html_params(**container_attrs), rendered_cb, item_image)


class StoriesCharacterSelect(StoriesImgSelect):
    def get_img_url(self, field, value):
        characters = {x.id: x for x in orm.select(c for c in Character)}  # NOTE: Pony ORM caches this
        return url_for('media', filename=characters[value].bundle.x32.webp)


class StoriesButtons(Select):
    def __init__(self, multiple=False):
        super().__init__(multiple=multiple)

    def __call__(self, field, **kwargs):
        attrs = dict(kwargs)
        btn_attrs = attrs.pop('btn_attrs', {})
        input_attrs = attrs.pop('input_attrs', {})
        btn_container_attrs = attrs.pop('btn_container_attrs', {})
        input_container_attrs = attrs.pop('input_container_attrs', {})
        btn_container = []
        input_container = []
        output = []
        for (option_value, option_label, selected, _render_kw) in field.iter_choices():
            btn = ButtonWidget()
            rendered_btn = btn(field, text=option_label, value=option_value, **btn_attrs)
            btn_container.append(rendered_btn)
            rb = Input('checkbox' if self.multiple else 'radio')
            if selected:
                rb_attrs = dict(input_attrs, value=option_value, checked='checked')
            else:
                rb_attrs = dict(input_attrs, value=option_value)
            rendered_rb = rb(field, id='{}_{}'.format(field.id, option_value), **rb_attrs)
            input_container.append(rendered_rb)
        btn = '<div %s>%s</div>' % (html_params(**btn_container_attrs), ' '.join(btn_container))
        data = '<div %s>%s</div>' % (html_params(**input_container_attrs), ' '.join(input_container))
        output.append(btn)
        output.append(data)
        return '\n'.join(output)


class ContactsWidget(object):
    def __call__(self, field, **kwargs):
        item_attrs_dict = kwargs.pop('item_attrs', None)

        attrs = ''
        for k, v in kwargs.items():
            attrs += ' {}="{}"'.format(escape(k), escape(v))

        item_attrs = ''
        if item_attrs_dict:
            for k, v in item_attrs_dict.items():
                item_attrs += ' {}="{}"'.format(escape(k), escape(v))

        output = ['<div%s>' % attrs]
        for contact in field:
            output.append('<div%s>' % item_attrs)
            output.append(contact.form.name())
            output.append(contact.form.value())
            if contact.errors:
                for errors in contact.errors.values():
                    for error in errors:
                        output.append('<span class="help-inline">{}</span>'.format(escape(error)))
            output.append('')
            output.append('</div>')
        output.append('<a href="#" class="contacts-add">{}</a>'.format(escape(gettext('Add new'))))
        output.append('</div>')
        return Markup('\n'.join(output))


class TagsInput(TextInput):
    def render_popup(self):
        return '<span class="input-tags-popup js-input-tags-popup popup-hidden"></span>'

    def __call__(self, field, **kwargs):
        input_html = super().__call__(field, **kwargs)
        return '<span class="input-tags js-input-tags">{}{}</span>'.format(
            input_html, self.render_popup()
        )
