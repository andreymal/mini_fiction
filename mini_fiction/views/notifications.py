#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Blueprint, jsonify, redirect, url_for, request
from flask_login import login_required
from pony.orm import db_session


bp = Blueprint('notifications', __name__)


@bp.route('/')
@db_session
@login_required
def index():
    if request.args.get('popup') == '1':
        return jsonify(popup='<h3>Здесь пока ничего нет</h3>', success=True)
    else:
        return redirect(url_for('index.index'))
