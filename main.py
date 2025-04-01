import os
import sys
import threading
from signal import pthread_kill, SIGINT
from flask import redirect, url_for, render_template
from flask_login import current_user
from flask_app import app, db, login, SFTP_ROOT, DATA_DIR
from flask_app.auth import bp as auth_bp
from flask_app.manager import bp as manager_bp
from flask_app.stmlrender import bp as stml_bp
from flask_app.models import User
from sftp_server.sftp import SFTPServer
from sftp_server.permissions_manager import PermissionsManager
from sftp_server.sqlite_auth import SQLiteAuth

_HOST_KEY = os.path.realpath(os.path.join(DATA_DIR, 'host_key'))
_sqlite_auth = SQLiteAuth(app, db)
_manager = PermissionsManager(authenticate=_sqlite_auth)
sftp_server = SFTPServer(SFTP_ROOT, _HOST_KEY, get_user=_manager.get_user)

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('manager.index'))
    return render_template('index.html')

def run_sftp_server():
    print("serving SFTP", flush=True)
    sftp_server.serve_forever('0.0.0.0', 5001)

def make_wsgi_app():
    with app.app_context():
        db.create_all()
    app.register_blueprint(auth_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(stml_bp)
    return app

if __name__ == '__main__' and os.getenv('DEBUG') == 'true':
    thread = threading.Thread(target=run_sftp_server, daemon=True)
    app = make_wsgi_app()
    #sftp_server.serve_forever('0.0.0.0', 5001)
    thread.start()
    app.run(host='0.0.0.0', debug=True, threaded=True)
    pthread_kill(thread.ident, SIGINT)
    thread.join()

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'sftp':
    run_sftp_server()