import os
import logging
import time
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

def get_mongo_client():
    """Lấy MongoDB client sử dụng models.py làm mẫu"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
            
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=30000,
                maxPoolSize=50,
                retryWrites=True,
                ssl=True,
                tlsAllowInvalidCertificates=True
            )
            
            client.admin.command('ping', serverSelectionTimeoutMS=10000)
            logging.info("[THÀNH CÔNG] Kết nối MongoDB Atlas thành công!")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logging.warning(f"[CẢNH BÁO] Lần thử {attempt}/{max_retries} kết nối MongoDB Atlas thất bại: {str(e)}")
            if attempt < max_retries:
                logging.info(f"Đợi {retry_delay} giây trước khi thử lại...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logging.error(f"[LỖI] Không thể kết nối MongoDB Atlas sau {max_retries} lần thử: {str(e)}")
                return None
        except Exception as e:
            logging.error(f"[LỖI] Lỗi kết nối MongoDB Atlas: {str(e)}")
            return None

def get_db_name():
    """Lấy tên cơ sở dữ liệu"""
    return "film-users"

def get_db_connection():
    """Lấy kết nối cơ sở dữ liệu MongoDB"""
    try:
        client = get_mongo_client()
        if client is None:
            return None, None
            
        dbname = get_db_name()
        db = client[dbname]
        return client, db
    except Exception as e:
        logger.error(f"Lỗi kết nối cơ sở dữ liệu: {str(e)}")
        return None, None

def init_mongo_indexes(db):
    """Khởi tạo index MongoDB"""
    try:
        try:
            # Create regular indexes first
            db.films.create_index("id", unique=True)
            db.films.create_index("title")
            db.genres.create_index("slug", unique=True)
            db.genres.create_index("id", unique=True)
            db.users.create_index("username", unique=True)
            db.favorites.create_index([("user_id", 1), ("film_id", 1)], unique=True)
            db.favorites.create_index("user_id")
            db.favorites.create_index("film_id")
            
            logging.info("Regular indexes created successfully")
            
            # Check for existing text index with improved handling
            index_info = db.films.index_information()
            text_index_exists = False
            for index_name, index_info in index_info.items():
                if 'weights' in index_info:  # Text indexes have weights
                    text_index_exists = True
                    logging.info(f"Existing text index found: {index_name}")
                    break
            
            if not text_index_exists:
                # Only create if no text index exists
                db.films.create_index(
                    [("title", "text"), ("description", "text")],
                    default_language="english"
                )
                logging.info("Text search index created successfully")
            else:
                logging.info("Text search index already exists - using existing index")
            
            return True
        except Exception as e:
            logging.warning(f"Một số index có thể đã tồn tại: {str(e)}")
            return True
    except Exception as e:
        logging.error(f"Lỗi khi tạo index MongoDB: {str(e)}")
        return False

def migrate_users_without_id(db):
    """Gán ID tuần tự cho người dùng không có ID"""
    try:
        users_without_id = list(db.users.find({"id": {"$exists": False}}))
        
        if not users_without_id:
            logging.info("Không tìm thấy người dùng nào không có ID")
            return True
            
        highest_user = db.users.find_one(sort=[("id", -1)])
        next_id = highest_user.get("id", 0) + 1 if highest_user else 1
        
        for user in users_without_id:
            db.users.update_one(
                {"_id": user["_id"]}, 
                {"$set": {"id": next_id}}
            )
            next_id += 1
            
        logging.info(f"Đã cập nhật {len(users_without_id)} người dùng với ID tuần tự")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi di chuyển người dùng không có ID: {str(e)}")
        return False

def initialize_database():
    """Khởi tạo cơ sở dữ liệu và các index cần thiết"""
    try:
        # Lấy MongoDB client
        client = get_mongo_client()
        if client is not None:
            # Lấy cơ sở dữ liệu
            db_name = get_db_name()
            db = client[db_name]
            
            # Di chuyển ID người dùng sang số tuần tự trước khi khởi tạo index
            migrate_users_without_id(db)
            
            # Khởi tạo index
            init_mongo_indexes(db)
            
            # Đóng kết nối
            client.close()
            logger.info(f"Kết nối MongoDB được khởi tạo cho cơ sở dữ liệu: {db_name}")
            return True
        else:
            logger.warning("Không thể khởi tạo kết nối MongoDB, ứng dụng sẽ chạy trong chế độ hạn chế")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo MongoDB: {str(e)}")
        return False
