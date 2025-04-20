import jwt

secret = 'aayujhtsrgabbhdgjccras'


# 编码
def encode(user_id):
    return jwt.encode({'user_id': user_id}, secret, algorithm='HS256')


def decode(encoded_jwt):
    return jwt.decode(encoded_jwt, secret, algorithms=['HS256'])
