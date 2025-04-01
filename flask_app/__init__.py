import os
from flask import Flask, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

SFTP_ROOT = os.environ.get('SFTP_ROOT')
DATA_DIR = os.environ.get('DATA_DIR')
DB_ABSPATH = os.path.join(DATA_DIR, 'db.sqlite')

app = Flask(__name__, instance_path=DATA_DIR)
app.wsgi_app = ProxyFix(app.wsgi_app)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:////{DB_ABSPATH}"
app.config['OAUTH2_PROVIDERS'] = {
    'discord': {
        'client_id': os.environ.get('DISCORD_CLIENT_ID'),
        'client_secret': os.environ.get('DISCORD_CLIENT_SECRET'),
        'authorize_url': 'https://discord.com/oauth2/authorize',
        'token_url': 'https://discord.com/api/oauth2/token',
        'scopes': ['guilds', 'guilds.members.read'],
    },
}
app.config['DISCORD_API'] = 'https://discord.com/api{}'
app.config['ALLOWED_GUILD'] = os.environ.get('DISCORD_ALLOWED_GUILD')
app.config['ALLOWED_ROLES'] = os.environ.get('DISCORD_ALLOWED_ROLES').split(',')

db = SQLAlchemy(app, model_class=Base)
login = LoginManager(app)
login.login_view = 'index'

def dlog(msg):
    app.logger.info(msg)
