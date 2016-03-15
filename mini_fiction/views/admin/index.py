#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template
from flask_babel import gettext
from pony.orm import db_session

from mini_fiction.utils.views import admin_required

bp = Blueprint('admin_index', __name__)


@bp.route('/')
@db_session
@admin_required
def index():
    return render_template('admin/index.html', page_title=gettext('Administration'))
