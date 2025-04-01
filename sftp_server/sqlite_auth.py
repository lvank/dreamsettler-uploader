import threading
from flask_app.models import User, DSPage

class AuthenticationError(Exception): pass


class SQLiteAuth(object):
    lock = threading.Lock()

    def __init__(self, app, db):
        self.app = app
        self.db = db

    def __call__(self, *args, **kwargs):
        return self.authenticate(*args, **kwargs)

    def authenticate(self, username, password):
        with self.lock:
            return self.authenticate_thread_unsafe(username, password)

    def authenticate_thread_unsafe(self, username, password):
        with self.app.app_context():
            user = self.db.session.scalar(self.db.select(User).where(User.sftp_user == username and User.sftp_pass == password))
            if not user:
                raise AuthenticationError()
            ds_pages = self.db.session.execute(self.db.select(DSPage).where(DSPage.user_id == user.id)).scalars().all()
            return [page.get_uri() for page in ds_pages]
