from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UserInfo(db.Model):
    """
    用户信息表
    """
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(255))
    password = db.Column(db.String(255))
    name = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'account': self.account,
            'name': self.name,
            'password': self.password
        }
