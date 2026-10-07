from app.auth.models import User


class UserStore:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def create(self, user: User) -> User:
        key = user.email.lower()
        if key in {item.email.lower() for item in self._users.values()}:
            raise ValueError("Email already registered")
        self._users[user.id] = user
        return user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized = email.lower()
        return next((item for item in self._users.values() if item.email.lower() == normalized), None)
