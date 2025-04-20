from flask import jsonify

from models import db, UserInfo


class DbUtil:

    @staticmethod
    def init_app(app):
        """初始化数据库连接"""
        db.init_app(app)
        with app.app_context():
            db.create_all()

    def authentication(self, params):
        return UserInfo.query.filter(UserInfo.account == params.get("account"),
                                     UserInfo.password == params.get("password")).first()

    def find_user(self, id):
        user = UserInfo.query.get(id)
        return user.to_dict()

    def add_user(self, data):
        """
        新增
        """
        # 查询
        exists = UserInfo.query.filter(UserInfo.account == data.get("account")).all()
        if exists:
            return jsonify({
                "code": 500,
                "msg": "用户账号已存在"
            })
        params = UserInfo(**data)
        db.session.add(params)
        db.session.commit()
        return jsonify({
            "code": 200,
        })