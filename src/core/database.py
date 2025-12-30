import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.config import MONGO_URI, DB_NAME

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.is_connected = False
        self._connect()

    def _connect(self):
        if not MONGO_URI:
            print("Warning: MONGO_URI not found. Database features disabled.")
            return

        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            # Перевірка з'єднання
            self.client.admin.command('ping')

            self.db = self.client[DB_NAME]
            self.collection = self.db["detections"]

            # Індекс для швидкого сортування за часом
            self.collection.create_index([("timestamp", DESCENDING)])

            self.is_connected = True
            print("Successfully connected to MongoDB Atlas.")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Failed to connect to MongoDB: {e}")
            self.is_connected = False

    def log_event(self, direction: str, track_id: int, confidence: float):
        """Записує подію входу/виходу бджоли."""
        if not self.is_connected:
            return

        event = {
            "timestamp": datetime.datetime.now(),
            "direction": direction,
            "track_id": int(track_id),
            "confidence": float(confidence)
        }

        try:
            self.collection.insert_one(event)
        except Exception as e:
            print(f"Error logging event: {e}")

    def get_stats(self):
        """Повертає загальну кількість входів та виходів."""
        if not self.is_connected:
            return {"in": 0, "out": 0}

        try:
            count_in = self.collection.count_documents({"direction": "in"})
            count_out = self.collection.count_documents({"direction": "out"})
            return {"in": count_in, "out": count_out}
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return {"in": 0, "out": 0}

    def get_recent_events(self, limit=10):
        """Повертає список останніх подій."""
        if not self.is_connected:
            return []

        try:
            cursor = self.collection.find(
                {},
                {"_id": 0, "timestamp": 1, "direction": 1, "track_id": 1}
            ).sort("timestamp", DESCENDING).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

# Глобальний екземпляр
db = DatabaseManager()