#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from urllib.request import Request, urlopen, quote

from mini_fiction.utils import random as utils_random


class BaseCaptcha:
    def __init__(self, app):
        pass

    def generate(self, lazy=True):
        '''Генерирует новую информацию для капчи. Возвращаемое значение должно
        быть словарём, который будет передан пользователю для рисования капчи.
        В словаре должно быть как минимум поле cls, указывающее путь
        до используемого класса капчи; остальное содержимое словаря
        произвольно.

        :param bool lazy: если True, то непосредственная генерация капчи может
          быть отложена на потом (например, при открытии специальной ссылки)
        :rtype: dict
        '''

        return {'cls': 'mini_fiction.captcha.BaseCaptcha'}

    def get_fields(self):
        '''Возвращает перечисление полей формы, которые ожидаются
        от пользователя при решении им капчи.
        '''

        return ()


    def copy_fields(self, dst, src):
        '''Вспомогательный метод, который копирует поля, которые возвращает
        метод get_fields, из второго словаря в первый при их наличии.
        Оригинальный словарь не меняет; возвращает его копию.
        '''

        dst = dict(dst)

        for k in self.get_fields():
            v = src.get(k)
            if v is not None:
                dst[k] = v

        return dst

    def check(self, form):
        '''Проверяет капчу, заполненную в указанной форме. Функция должна
        возвращать True или False в зависимости от того, пройдена капча
        или нет.

        :param form: dict-подобный объект, непосредственно содержимое
          пользовательской формы. Никак не валидируется, поэтому поля капчи
          могут вообще отсутствовать
        :rtype: bool
        '''

        return True

    def check_or_raise(self, form):
        '''Если проверка капчи методом check не пройдёт, кидает CaptchaError.

        :param form: dict-подобный объект, непосредственно содержимое
          пользовательской формы. Никак не валидируется, поэтому поля капчи
          могут вообще отсутствовать
        :rtype: bool
        '''

        result = self.check(form)
        if not result:
            raise CaptchaError
        return result


class PyCaptcha(BaseCaptcha):
    def __init__(self, app):
        from captcha.image import ImageCaptcha  # pip install captcha

        super().__init__(app)
        self.app = app

        self.fonts = app.config['PYCAPTCHA_FONTS']
        self.prefix = app.config['PYCAPTCHA_CACHE_PREFIX']
        self.chars = app.config['PYCAPTCHA_CHARS']
        self.case_sens = app.config['PYCAPTCHA_CASE_SENSITIVE']
        self.length = app.config['PYCAPTCHA_LENGTH']

        rnd = utils_random.randrange(10**11, 10**12)
        k = self.prefix + '_cache_test_{}'.format(rnd)
        self.app.cache.set(k, rnd, timeout=10)
        if self.app.cache.get(k) != rnd:
            raise RuntimeError('PyCaptcha requires working cache (e.g. memcached)')

        self.generator = ImageCaptcha(fonts=self.fonts)

        self.bind_captcha_views()

    def bind_captcha_views(self):
        from flask import Blueprint

        bp = Blueprint('pycaptcha', __name__)
        bp.route('/captcha/<int:captcha_id>.jpg')(self.captcha_view)
        self.app.register_blueprint(bp)

    def _draw_and_save_image(self, captcha_id):
        from io import BytesIO

        solution = utils_random.random_string(self.length, self.chars)

        with self.generator.generate_image(solution) as im:  # class PIL.Image
            data = BytesIO()
            im.save(data, format='JPEG', quality=55)
        data = data.getvalue()
        tm = time.time()

        k = self.prefix + str(captcha_id)
        self.app.cache.set(k, [tm, data, solution], timeout=7200)
        return data

    def captcha_view(self, captcha_id):
        from flask import abort, make_response

        k = self.prefix + str(captcha_id)
        result = self.app.cache.get(k)
        if result is None:
            abort(404)

        if time.time() - result[0] > 1:
            data = self._draw_and_save_image(captcha_id)
        else:
            data = result[1]

        response = make_response(data)
        response.headers['Content-Type'] = 'image/jpeg'
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers['Cache-Control'] = 'public, max-age=0'

        return response

    def generate(self, lazy=True):
        captcha_id = utils_random.randrange(10**11, 10**12)
        k = 'pycaptcha_{}'.format(captcha_id)

        self.app.cache.set(k, [0, b'', ''], timeout=7200)
        if self.app.cache.get(k) != [0, b'', '']:
            raise RuntimeError('PyCaptcha requires working cache (e.g. memcached)')

        if not lazy:
            self._draw_and_save_image(captcha_id)

        return {'cls': 'mini_fiction.captcha.PyCaptcha', 'pycaptcha_id': str(captcha_id)}

    def get_fields(self):
        return ('captcha_id', 'captcha_solution')

    def check(self, form):
        captcha_id = form.get('captcha_id')
        solution = form.get('captcha_solution')

        if isinstance(captcha_id, str):
            if captcha_id.isdigit():
                captcha_id = int(captcha_id)

        if not captcha_id or not solution:
            return False

        if not isinstance(solution, str) or len(solution) > 254 or not isinstance(captcha_id, int):
            return False

        k = self.prefix + str(captcha_id)
        result = self.app.cache.get(k)

        if not result:
            return False
        result = result[2]

        self.app.cache.set(k, None, timeout=10)

        if not self.case_sens:
            solution = solution.lower()
            result = result.lower()

        return solution == result


class ReCaptcha(BaseCaptcha):
    def __init__(self, app):
        super().__init__(app)
        if 'RECAPTCHA_PUBLIC_KEY' not in app.config or 'RECAPTCHA_PRIVATE_KEY' not in app.config:
            raise ValueError('RECAPTCHA_PUBLIC_KEY and RECAPTCHA_PRIVATE_KEY configs are required')
        self.key = app.config['RECAPTCHA_PUBLIC_KEY']
        self.private_key = app.config['RECAPTCHA_PRIVATE_KEY']
        self.user_agent = app.user_agent

    def generate(self, lazy=True):
        return {'cls': 'mini_fiction.captcha.ReCaptcha', 'recaptcha_key': self.key}

    def get_fields(self):
        return ('g-recaptcha-response',)

    def check(self, form):
        resp = form.get('g-recaptcha-response')
        if not resp or not isinstance(resp, str) or len(resp) > 8192:
            return False

        req = Request('https://www.google.com/recaptcha/api/siteverify')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('User-Agent', self.user_agent)
        req.data = 'secret={}&response={}'.format(
            quote(self.private_key), quote(resp)
        ).encode('utf-8')

        try:
            answer = urlopen(req, timeout=20).read()
            answer = dict(json.loads(answer.decode('utf-8')))
        except Exception:
            return False

        return bool(answer.get('success'))


class CaptchaError(ValueError):
    # TODO: refactor exceptions
    pass
