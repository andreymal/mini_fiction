# -*- coding: utf-8 -*-

import weakref


class BaseBL(object):
    _model = None

    def __init__(self, model):
        self._model = weakref.ref(model)

    @property
    def model(self):
        return self._model()
