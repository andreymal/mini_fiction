#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class BaseVoting:
    def __init__(self, app):
        pass

    def get_default_vote_value(self):
        '''Данный метод должен возвращать целое число — значение рейтинга,
        которое будет присвоено только что созданному рассказу
        (``vote_value``).

        :rtype: int
        '''
        raise NotImplementedError

    def get_default_vote_extra(self):
        '''Данный метод должен возвращать словарь, закодированный в JSON —
        значение поля ``vote_extra`` для только что созданного рассказа.

        :rtype: str
        '''
        raise NotImplementedError

    def validate_value(self, value):
        '''Возвращает True, если переданное целое число является корректным
        значением для оценки рассказа.

        :param int value: оценка пользователя
        :rtype: bool
        '''

        raise NotImplementedError

    def can_show(self, story):
        '''Возвращает True, если рейтинг данного расказа можно посмотреть.

        :param story: рассказ (объект Story)
        :rtype: bool
        '''
        from flask import current_app
        return story.vote_total >= current_app.config['MINIMUM_VOTES_FOR_VIEW']


    def update_rating(self, story):
        '''Обновляет ``vote_total``, ``vote_value`` и ``vote_extra`` у данного
        рассказа. Как правило, вызывается сразу после оценивания рассказа
        пользователем.

        :param story: обновляемый рассказ (объект Story)
        '''

        raise NotImplementedError

    def vote_view_html(self, story, user=None, full=False):
        '''Возвращает HTML-код для отображения средней оценки рассказа возле
        его заголовка.

        :param story: рассказ (объект Story)
        :param user: пользоватль, для которого генерируем HTML-код (может быть
          None, AnonymousUser или Author)
        :param bool full: True, если оценка отображается на странице чтения
          рассказа, и False на второстепенных страницах (вроде списков
          рассказов)
        :rtype: str
        '''

        return ''

    def vote_area_1_html(self, story, user=None, user_vote=None):
        '''Возвращает HTML-код для отображения формы оценивания рассказа
        возле его заголовка.

        Возвращаемый HTML-код должен быть обязательно обёрнут в форму вида
        ``<form method="POST" action="{{ url_for('story.vote', pk=story.id) }}">``.
        Кнопки для голосования должны быть input/button с классом
        ``js-vote-button``, иметь имя поля ``vote_value`` и целое число
        в качестве значения; также в форме должен присутствовать csrf_token.

        :param story: рассказ (объект Story)
        :param user: пользоватль, для которого генерируем HTML-код (может быть
          None, AnonymousUser или Author)
        :param user_vote: объект Vote, если пользователь уже голосовал ранее
        :rtype: str
        '''

        return ''

    def vote_area_2_html(self, story, user=None, user_vote=None):
        '''Возвращает HTML-код для отображения формы оценивания под его
        заголовком и перед описанием.

        Возвращаемый HTML-код должен быть обязательно обёрнут в форму вида
        ``<form method="POST" action="{{ url_for('story.vote', pk=story.id) }}">``.
        Кнопки для голосования должны быть input/button с классом
        ``js-vote-button``, иметь имя поля ``vote_value`` и целое число
        в качестве значения; также в форме должен присутствовать csrf_token.

        :param story: рассказ (объект Story)
        :param user: пользоватль, для которого генерируем HTML-код (может быть
          None, AnonymousUser или Author)
        :param user_vote: объект Vote, если пользователь уже голосовал ранее
        :rtype: str
        '''

        return ''
