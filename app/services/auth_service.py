from app.repositories import user_repository
from app.utils.security import hash_pw


def authenticate(username, password):
    return bool(user_repository.find(username.strip(), hash_pw(password)))
