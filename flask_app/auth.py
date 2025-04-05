from flask import Blueprint, redirect, url_for, flash, session, current_app, request, abort, render_template
from urllib.parse import urlencode
import requests
import secrets
from flask_login import login_user, logout_user, current_user
from flask_app import db
from flask_app.models import User

bp = Blueprint('auth', __name__, template_folder='templates', url_prefix='/auth')


@bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))


@bp.route('/sftp_cred')
def sftp_cred():
    return render_template('sftp_cred.html', user=current_user)

@bp.route('/init/<provider>')
def oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('manager.index'))

    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session['oauth2_state'] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode({
        'client_id': provider_data['client_id'],
        'redirect_uri': url_for('auth.oauth2_callback', provider=provider,
                                _external=True),
        'response_type': 'code',
        'scope': ' '.join(provider_data['scopes']),
        'state': session['oauth2_state'],
    })

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data['authorize_url'] + '?' + qs)

@bp.route('/callback/<provider>')
def oauth2_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('manager.index'))

    provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if 'error' in request.args:
        for k, v in request.args.items():
            if k.startswith('error'):
                flash(f'{k}: {v}')
        return redirect(url_for('index'))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args['state'] != session.get('oauth2_state'):
        abort(401)

    # make sure that the authorization code is present
    if 'code' not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    oauth2_token = current_app.config.get('DEBUG_OAUTH2_TOKEN')
    if not oauth2_token:
        response = requests.post(provider_data['token_url'], data={
            'client_id': provider_data['client_id'],
            'client_secret': provider_data['client_secret'],
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': url_for('auth.oauth2_callback', provider=provider,
                                    _external=True),
        }, headers={'Accept': 'application/json'})
        if response.status_code != 200:
            abort(401)
        oauth2_token = response.json().get('access_token')
    if not oauth2_token:
        abort(401)
    apiurl = current_app.config['DISCORD_API']
    guild_id = current_app.config['ALLOWED_GUILD']
    guild_q = requests.get(apiurl.format(f'/users/@me/guilds/{guild_id}/member'),
                            headers={'Accept': 'application/json', 'Authorization': f'Bearer {oauth2_token}'})
    if guild_q.status_code != 200:
        abort(401, description='Not a member of the Dreamsettler Discord')
    
    guild_result = guild_q.json()
    roles = guild_result.get('roles')
    allowed_role = False
    for role in roles:
        if role in current_app.config['ALLOWED_ROLES']:
            allowed_role = True
            break
    if not allowed_role:
        abort(401, description='Missing a required role in the Dreamsettler Discord')

    id = guild_result['user']['id']
    username = guild_result['user']['username']

    # find or create the user in the database
    user = db.session.scalar(db.select(User).where(User.id == id))
    if user is None:
        user = User(id=id, username=username, sftp_user=secrets.token_urlsafe(16), sftp_pass=secrets.token_urlsafe(24))
        db.session.add(user)
        db.session.commit()

    # log the user in
    login_user(user)
    return redirect(url_for('manager.index'))
