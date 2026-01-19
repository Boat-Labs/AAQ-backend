class Database:
    def __init__(self, url: str):
        self.url = url

    def connect(self):
        return True


_db = None


def get_database(url: str):
    global _db
    if _db is None:
        _db = Database(url)
    return _db
