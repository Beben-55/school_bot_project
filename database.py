from typing import Dict, Optional

class InMemoryDB:
    def __init__(self):
        self._storage: Dict[int, str] = {}

    async def set_user_class(self, user_id: int, user_class: str) -> None:
        self._storage[user_id] = user_class.strip().upper()

    async def get_user_class(self, user_id: int) -> Optional[str]:
        return self._storage.get(user_id)

db = InMemoryDB()
