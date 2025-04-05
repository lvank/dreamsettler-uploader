import flask
from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from flask_app import db, SFTP_ROOT, dlog
from flask_app.models import DSPage
from flask_app.stmlparse import re_pagename
from sqlalchemy.exc import IntegrityError
import re
import os

re_username = re.compile(r'^[a-z][a-z0-9_]{2,64}$')
bp = Blueprint('manager', __name__, template_folder='templates', url_prefix='/manager')

@bp.route('/')
@login_required
def index():
    return render_template('manager.html')

@bp.route('/pages')
@login_required
def pages():
    delete_pagetype = flask.request.args.get('delete_pagetype')
    delete_pagename = flask.request.args.get('delete_pagename')
    ds_pages = db.session.execute(db.select(DSPage).where(DSPage.user_id == current_user.id)).scalars().all()
    return render_template('pages.html', ds_pages=ds_pages, delete_page=[delete_pagetype, delete_pagename])

@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    delete_pagetype = flask.request.form.get('delete_pagetype')
    delete_pagename = flask.request.form.get('delete_pagename')
    if not delete_pagetype or not delete_pagename or delete_pagetype not in ("0", "1"):
        return _flash_pages("Invalid request.")
    delete_pagetype = int(delete_pagetype)
    # Should never be able to find multiple results, pagetype+name has unique constraint.
    ds_page: DSPage = db.session.execute(db.select(DSPage).where(DSPage.page_type == delete_pagetype, DSPage.page_name == delete_pagename)).scalar_one_or_none()
    if not ds_page:
        return _flash_pages("Page not found.")
    if ds_page.user_id != current_user.id:
        return _flash_pages("No permissions to delete someone else's page.")
    db.session.delete(ds_page)
    try:
        os.rmdir(os.path.join(SFTP_ROOT, ds_page.get_uri()))
        flash("Page deleted.")
        db.session.commit()
    except OSError:
        db.session.rollback()
        flash("Directory is not yet empty.")
    except FileNotFoundError:
        db.session.rollback()
        flash("Directory was found. This actually shouldn't happen, please report this.")
    finally:
        return pages()

def _flash_pages(msg):
    flash(msg)
    return pages()

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if flask.request.method == 'GET':
        return render_template('create_page_form.html')
    pagetype = flask.request.values.get('pagetype', None)
    errors={}
    if pagetype not in ['0', '1']:
        errors['general'] = 'Invalid page type'
        return render_template('create_page_form.html', errors=errors) 
    pagetype = int(pagetype)
    
    pagename = flask.request.values.get('pagename')
    if pagetype == 0:
        if len(pagename) < 3:
            errors['pagename'] = 'Username is too short (3 chars minimum)'
        elif not re_username.match(pagename):
            errors['pagename'] = 'Username must contain only letters/numbers and start with a number'
    elif pagetype == 1:
        if pagename == 'dreamsettler.zed':
            errors['pagename'] = 'No!!!!! >:('
        elif not re_pagename.match(pagename):
            errors['pagename'] = 'Domain must start with a letter, have only letters/numbers/dashes, and end in .zed/som/nap'
        elif '--' in pagename:
            errors['pagename'] = 'Domain cannot have two subsequent dashes'

    if errors:
        return render_template('create_page_form.html', errors=errors, pars=flask.request.values)

    page = DSPage(user_id = current_user.id, page_type = pagetype, page_name = pagename)
    db.session.add(page)
    try:
        os.makedirs(os.path.join(SFTP_ROOT, page.get_uri()))
        db.session.commit()
    except (IntegrityError, OSError) as e:
        dlog(e)
        errors['general'] = 'This page already exists.'
        return render_template('create_page_form.html', errors=errors, pars=flask.request.values)
    resp = flask.make_response(render_template('create_page_button.html'))
    resp.headers.set('HX-Refresh', 'true')
    return resp
