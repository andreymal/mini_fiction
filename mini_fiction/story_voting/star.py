#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from statistics import mean, pstdev

from pony import orm
from flask import current_app, render_template

from mini_fiction.story_voting.base import BaseVoting


class StarVoting(BaseVoting):
    '''Классический рейтинг рассказа в виде звёзд.

    Используемые настройки:

    - ``VOTING_MAX_VALUE`` — число звёзд
    - ``MINIMUM_VOTES_FOR_VIEW`` — минимальное число оценок, после которого
      рейтинг рассказа становится виден

    '''

    def get_default_vote_value(self):
        return int(current_app.config['VOTES_MID'] * 100)

    def get_default_vote_extra(self):
        return '{"average": 3.0, "stddev": 0.0}'

    def validate_value(self, value):
        return isinstance(value, int) and value >= 1 and value <= current_app.config['VOTING_MAX_VALUE']

    def update_rating(self, story):
        from mini_fiction.models import Vote

        votes = orm.select(x.vote_value for x in Vote if x.story == story).without_distinct()[:]
        votes = [min(x, current_app.config['VOTING_MAX_VALUE']) for x in votes]
        votes = [max(1, x) for x in votes]
        m = mean(votes) if votes else 3.0

        # Это называют алгоритмом Томаса Байеса https://i.imgur.com/z0bRn9a.gif
        n = current_app.config['MINIMUM_VOTES_FOR_VIEW']
        votes_mid = current_app.config['VOTES_MID']
        count = len(votes)

        v1 = count / (count + n) * m
        v2 = n / (count + n) * votes_mid
        story.vote_value = int((v1 + v2) * 100)

        story.vote_total = count

        extra = json.loads(story.vote_extra)
        extra['average'] = round(float(m), 6)
        extra['stddev'] = round(pstdev(votes, m) if votes else 0.0, 6)
        story.vote_extra = json.dumps(extra, ensure_ascii=False, sort_keys=True)

    # templates

    def can_show_stars(self, story):
        return story.vote_total and self.can_show(story)

    def stars(self, story, extra=None):
        if not self.can_show_stars(story):
            return [6] * current_app.config['VOTING_MAX_VALUE']

        if not extra:
            extra = json.loads(story.vote_extra)

        stars = []
        avg = extra.get('average') or 0.0
        devmax = avg + (extra.get('stddev') or 0.0)

        for i in range(1, current_app.config['VOTING_MAX_VALUE'] + 1):
            if avg >= i - 0.25:
                # полная звезда
                stars.append(5)
            elif avg >= i - 0.75:
                # половина звезды
                stars.append(4 if devmax >= i - 0.25 else 3)
            elif devmax >= i - 0.25:
                # пустая звезда (с полным отклонением)
                stars.append(2)
            else:
                # пустая звезда (с неполным отклонением)
                stars.append(1 if devmax >= i - 0.75 else 0)

        return stars

    def vote_view_html(self, story, user=None, full=False):
        extra = json.loads(story.vote_extra)

        ctx = {
            'story': story,
            'can_show_stars': self.can_show_stars(story),
            'vote_total': story.vote_total,
            'vote_average': extra.get('average') or 0.0,
            'vote_stddev': extra.get('stddev') or 0.0,
            'star_ids': self.stars(story, extra=extra),
            'full': full,
            'stars_count': current_app.config['VOTING_MAX_VALUE'],
        }

        return render_template('includes/story_voting/stars/vote_view.html', **ctx)

    def vote_area_1_html(self, story, user=None, user_vote=None):
        return ''

    def vote_area_2_html(self, story, user=None, user_vote=None):
        if not user or not user.is_authenticated or story.bl.is_author(user):
            return ''

        ctx = {
            'story': story,
            'vote': user_vote,
            'stars_count': current_app.config['VOTING_MAX_VALUE'],
        }

        return render_template('includes/story_voting/stars/vote_area_2.html', **ctx)
