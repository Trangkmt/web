from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import ssl
from functools import lru_cache
import time
import threading

# MongoDB connection settings with optimized options
uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
dbname = "film-users"

# Connection pool management with thread safety
_mongo_client = None
_client_lock = threading.Lock()

# Cache management for database operation results
_cache = {}
_cache_ttl = 300  # 5 minutes TTL for cache entries
_cache_lock = threading.Lock()

# Connect to MongoDB with optimized settings
try:
    with _client_lock:
        if _mongo_client is None:
            _mongo_client = MongoClient(
                uri,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000,
                socketTimeoutMS=10000,
                maxPoolSize=20,                 # Optimal pool size for web traffic
                minPoolSize=5,                  # Keep minimum connections in pool
                maxIdleTimeMS=60000,            # Close idle connections after 60 seconds
                retryWrites=True,
                ssl=True,
                tlsAllowInvalidCertificates=True,
                appname="phim-neu-app",
                waitQueueTimeoutMS=1000,        # Fast failure if queue wait is too long
            )
            
            # Verify connection is fast
            _mongo_client.admin.command('ping', serverSelectionTimeoutMS=2000)
            print("[SUCCESS] MongoDB Atlas connection successful!")
            
            # Initialize collections
            db = _mongo_client[dbname]
            films_collection = db.films
            genres_collection = db.genres
            users_collection = db.users
            favorites_collection = db.favorites
            
            # Build indexes if they don't exist
            # Create multikey indexes for faster search
            try:
                # Create regular indexes first
                films_collection.create_index("id", unique=True)
                films_collection.create_index("genre_ids")
                films_collection.create_index("status")
                films_collection.create_index("release_year")
                films_collection.create_index("rating")
                
                genres_collection.create_index("id", unique=True)
                genres_collection.create_index("name")
                
                favorites_collection.create_index([("user_id", 1), ("film_id", 1)], unique=True)
                favorites_collection.create_index("user_id")
                
                # Check for existing text index before creating
                index_info = films_collection.index_information()
                text_index_exists = any('text' in str(v.get('key', [])) for v in index_info.values())
                
                if not text_index_exists:
                    films_collection.create_index([("title", "text"), ("description", "text")])
                    print("[THÔNG TIN] Text index đã được tạo")
                else:
                    print("[THÔNG TIN] Text index đã tồn tại - sử dụng index hiện có")
                
                print("[THÔNG TIN] Index MongoDB đã được tạo hoặc xác minh")
            except Exception as e:
                print(f"[CẢNH BÁO] Lỗi khi tạo index: {str(e)}")
            
            # Báo cáo trạng thái collection nhưng giữ nhẹ nhàng
            total_films = db.command("collstats", "films").get("count", 0)
            total_genres = db.command("collstats", "genres").get("count", 0)
            
            print(f"[THÔNG TIN] Đã kết nối tới các collection: films ({total_films} tài liệu), "
                f"genres ({total_genres} tài liệu)")
except Exception as e:
    print(f"[LỖI] Lỗi kết nối MongoDB Atlas: {str(e)}")
    
    # Create minimal dummy collection with reduced code
    class DummyCollection:
        def __getattr__(self, name):
            return lambda *args, **kwargs: self._dummy_return(name)
            
        def _dummy_return(self, name):
            if name == 'find':
                return DummyCursor()
            elif name == 'insert_one':
                return type('obj', (object,), {'inserted_id': 'dummy_id'})
            elif name == 'find_one':
                return None
            elif name == 'aggregate':
                return []
            else:
                return None
    
    class DummyCursor:
        def __init__(self): self.data = []
        def __getattr__(self, name): return lambda *args, **kwargs: self
        def __iter__(self): return iter([])
        def __getitem__(self, key): return None
        def __len__(self): return 0
    
    # Initialize dummy objects
    _mongo_client = None
    db = None
    films_collection = DummyCollection()
    genres_collection = DummyCollection()
    users_collection = DummyCollection()
    favorites_collection = DummyCollection()

# Optimize ID serialization with larger cache
@lru_cache(maxsize=2048)
def serialize_id(obj):
    """Convert MongoDB ObjectId to string for JSON serialization with improved caching"""
    if isinstance(obj, dict) and '_id' in obj and isinstance(obj['_id'], ObjectId):
        obj = dict(obj)  # Create a copy to avoid modifying the original
        obj['_id'] = str(obj['_id'])
    return obj

# Cache decorator để tối ưu các hàm lấy dữ liệu thường xuyên sử dụng
def cached(ttl=_cache_ttl):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            with _cache_lock:
                # Check if result is in cache and not expired
                if key in _cache:
                    result, expire_time = _cache[key]
                    if expire_time > time.time():
                        return result
            
            # Call the function if not cached or expired
            result = func(*args, **kwargs)
            
            # Cache the result
            with _cache_lock:
                _cache[key] = (result, time.time() + ttl)
            
            return result
        return wrapper
    return decorator

# Áp dụng decorator cho các hàm tìm kiếm phim
@cached(ttl=300)  # Cache 5 phút
def find_films_by_genre(genre_id, limit=20, skip=0):
    """Find films by genre with caching"""
    try:
        films = list(films_collection.find(
            {"genre_ids": genre_id}, 
            {"_id": 1, "id": 1, "title": 1, "poster_path": 1, "rating": 1}
        ).sort("rating", -1).skip(skip).limit(limit))
        
        return [serialize_id(film) for film in films]
    except Exception as e:
        print(f"Error finding films by genre: {str(e)}")
        return []

# Find film by ID with optimization and caching
@lru_cache(maxsize=512)
def find_film_by_id(film_id, projection=None):
    """Find film by ID with optimized approach and caching"""
    if not projection:
        projection = {
            "_id": 1, "id": 1, "title": 1, "poster_path": 1, 
            "description": 1, "rating": 1, "genre_ids": 1, 
            "release_year": 1, "video_url": 1
        }
    
    # Try numeric ID first (most common case)
    if isinstance(film_id, (int, str)) and str(film_id).isdigit():
        film_id_int = int(film_id)
        film = films_collection.find_one({"id": film_id_int}, projection)
        if film:
            return serialize_id(film)
    
    # Try ObjectId if numeric ID fails
    if isinstance(film_id, str) and len(film_id) == 24:
        try:
            film = films_collection.find_one({"_id": ObjectId(film_id)}, projection)
            if film:
                return serialize_id(film)
        except:
            pass
    
    return None

# Tối ưu hóa truy vấn tìm kiếm
@cached(ttl=60)  # Cache 1 phút cho kết quả tìm kiếm
def search_films(query, limit=20, skip=0):
    """Search films with optimized query and caching"""
    try:
        # Sử dụng text search cho truy vấn dài hơn 3 ký tự
        if len(query) > 3:
            try:
                # Try text search first
                results = list(films_collection.find(
                    {"$text": {"$search": query}},
                    {"score": {"$meta": "textScore"}, "_id": 1, "id": 1, "title": 1, 
                     "poster_path": 1, "rating": 1, "description": 1}
                ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit))
                
                # If no results from text search, fall back to regex
                if not results:
                    print(f"Text search returned no results, falling back to regex for: '{query}'")
                    return search_with_regex(query, limit, skip)
                    
                return [serialize_id(film) for film in results]
            except Exception as text_error:
                # If text search fails for any reason, fall back to regex
                print(f"Text search failed, error: {str(text_error)}. Falling back to regex for: '{query}'")
                return search_with_regex(query, limit, skip)
        else:
            # Always use regex for short queries
            return search_with_regex(query, limit, skip)
    except Exception as e:
        print(f"Error searching films: {str(e)}")
        return []

def search_with_regex(query, limit=20, skip=0):
    """Fallback search using regex instead of text search"""
    try:
        results = list(films_collection.find(
            {"$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}}
            ]},
            {"_id": 1, "id": 1, "title": 1, "poster_path": 1, "rating": 1, "description": 1}
        ).skip(skip).limit(limit))
        
        return [serialize_id(film) for film in results]
    except Exception as e:
        print(f"Error in regex search: {str(e)}")
        return []

# Import models
from .film import Film
from .genre import Genre
from .user import User
from .favorite import Favorite
from .database import init_database, create_api_app, create_web_app

# Export all models and functions
__all__ = ['Film', 'Genre', 'User', 'Favorite', 'init_database', 
           'create_api_app', 'create_web_app', 'find_film_by_id',
           'db', 'films_collection', 'genres_collection', 
           'users_collection', 'favorites_collection', 'serialize_id',
           'search_films', 'find_films_by_genre', 'cached']
