from flask_login import UserMixin
from flask_app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger(), primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    sftp_user = db.Column(db.String(16), nullable=False)
    sftp_pass = db.Column(db.String(24), nullable=False)

class DSPage(db.Model):
    __tablename__ = 'pages'
    __table_args__ = (db.UniqueConstraint('page_type', 'page_name'), )
    user_id = db.Column(db.BigInteger(), db.ForeignKey('users.id'), primary_key=True)
    page_type = db.Column(db.Integer(), primary_key=True)
    page_name = db.Column(db.String(32), primary_key=True)

    def get_uri(self):
        # DS username
        if self.page_type == 0:
            return f"dreamsettler.zed/~{self.page_name}"
        else:
            # page_type == 1 -> own TLD
            return self.page_name