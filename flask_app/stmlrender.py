from flask import send_from_directory, Blueprint, make_response
from flask_login import login_required
from flask_app import SFTP_ROOT
from flask_app.stmlparse import stml_to_html
import os
import re

bp = Blueprint('stmlrender', __name__, url_prefix='/browse')

@bp.route('/')
@bp.route('/<path:path>')
@login_required
def pages(path='./'):
    rpath = os.path.realpath(os.path.join(SFTP_ROOT, path))
    if not re.match(f'^{SFTP_ROOT}($|/)', rpath):
        return make_response('File not found', 404)
    if re.search(r'\.stml?$', rpath):
        with open(rpath) as file:
            return stml_parse(file.read())
    if os.path.isdir(rpath):
        response = ''
        for f in os.listdir(rpath):
            if f == 'main.stm' or f == 'main.stml':
                stml_path = os.path.realpath(os.path.join(rpath, f))
                with open(stml_path) as file:
                    return stml_parse(file.read())
            response += f'<li><a href="{f}/">{f}</a></li>\n'
        return make_response(response)
    return send_from_directory(SFTP_ROOT, path)
    
def stml_parse(stml_str):
    html = stml_to_html('/browse', stml_str)
    return make_response(html)