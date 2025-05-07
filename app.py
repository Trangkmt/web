import os
import logging
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from bson.objectid import ObjectId
from datetime import datetime

from routes.auth_routes import register_auth_routes
from routes.admin_routes import register_admin_routes
from routes.film_routes import register_film_routes
from routes.error_handlers import register_error_handlers
from routes.user_routes import register_user_routes
from routes.favorite_film import favorite_bp

# Import model Favorite
from models.favorite import Favorite

# Thử import tiện ích cơ sở dữ liệu
try:
    from utils.db import get_mongo_client, get_db_name, init_mongo_indexes, migrate_users_without_id
except ImportError:
    # Triển khai dự phòng dựa trên models.py khi không tìm thấy utils.db
    from pymongo import MongoClient
    import os
    
    def get_mongo_client():
        """Lấy MongoDB client sử dụng models.py làm mẫu
        
        Chức năng:
        - Tạo kết nối đến MongoDB Atlas với cấu hình tối ưu
        - Xử lý lỗi và ghi log thích hợp
        - Kiểm tra kết nối bằng lệnh ping
        
        Returns:
            MongoClient: Đối tượng kết nối MongoDB, hoặc None nếu có lỗi
        """
        try:
            uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
            
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                retryWrites=True,
                ssl=True,
                tlsAllowInvalidCertificates=True
            )
            
            # Kiểm tra kết nối ngay lập tức
            client.admin.command('ping')
            logging.info("[THÀNH CÔNG] Kết nối MongoDB Atlas thành công!")
            return client
        except Exception as e:
            logging.error(f"[LỖI] Lỗi kết nối MongoDB Atlas: {str(e)}")
            return None
    
    def get_db_name():
        """Lấy tên cơ sở dữ liệu
        
        Returns:
            str: Tên cơ sở dữ liệu
        """
        return "film-users"
    
    def init_mongo_indexes(db):
        """Khởi tạo index MongoDB sử dụng cách tiếp cận đơn giản hóa
        
        Chức năng:
        - Tạo các index cơ bản với xử lý lỗi
        - Index cho phim: id, title, text search
        - Index cho thể loại: slug, id
        - Index cho người dùng: username
        - Index cho yêu thích: user_id+film_id, user_id
        
        Args:
            db: Đối tượng cơ sở dữ liệu MongoDB
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Tạo index cơ bản với xử lý lỗi
            try:
                db.films.create_index("id", unique=True)
                db.films.create_index("title")
                
                # Index tìm kiếm văn bản với trọng số mặc định để tránh xung đột
                db.films.create_index([("title", "text"), ("description", "text")], 
                                   default_language="english")
                
                db.genres.create_index("slug", unique=True)
                db.genres.create_index("id", unique=True)
                
                db.users.create_index("username", unique=True)
                
                db.favorites.create_index([("user_id", 1), ("film_id", 1)], unique=True)
                db.favorites.create_index("user_id")
                
                logging.info("Index MongoDB được tạo thành công")
                return True
            except Exception as e:
                logging.warning(f"Một số index có thể đã tồn tại: {str(e)}")
                return True
        except Exception as e:
            logging.error(f"Lỗi khi tạo index MongoDB: {str(e)}")
            return False
    
    def migrate_users_without_id(db):
        """Gán ID tuần tự cho người dùng không có ID
        
        Chức năng:
        - Tìm người dùng không có trường ID
        - Gán ID tuần tự bắt đầu từ ID cao nhất hiện có
        
        Args:
            db: Đối tượng cơ sở dữ liệu MongoDB
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Tìm người dùng không có trường ID
            users_without_id = list(db.users.find({"id": {"$exists": False}}))
            
            if not users_without_id:
                logging.info("Không tìm thấy người dùng nào không có ID")
                return True
                
            logging.info(f"Tìm thấy {len(users_without_id)} người dùng không có ID")
            
            # Tìm ID cao nhất hiện có
            highest_user = db.users.find_one(sort=[("id", -1)])
            next_id = highest_user.get("id", 0) + 1 if highest_user else 1
            
            # Cập nhật người dùng
            for user in users_without_id:
                db.users.update_one(
                    {"_id": user["_id"]}, 
                    {"$set": {"id": next_id}}
                )
                next_id += 1
                
            logging.info(f"Cập nhật {len(users_without_id)} người dùng với ID tuần tự")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi di chuyển người dùng không có ID: {str(e)}")
            return False

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', mode='a', encoding='utf-8', delay=True),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Hàm kết nối MongoDB
def get_db_connection():
    """Lấy kết nối cơ sở dữ liệu MongoDB
    
    Chức năng:
    - Tạo kết nối đến MongoDB Atlas với cấu hình tối ưu
    - Xử lý lỗi và ghi log thích hợp
    
    Returns:
        tuple: (MongoClient, Database) hoặc (None, None) nếu có lỗi
    """
    try:
        from pymongo import MongoClient
        uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
        dbname = os.environ.get('MONGO_DBNAME', "film-users")
        
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            maxPoolSize=50,
            ssl=True,
            tlsAllowInvalidCertificates=True,
            retryWrites=True
        )
        db = client[dbname]
        return client, db
    except Exception as e:
        logger.error(f"Lỗi kết nối cơ sở dữ liệu: {str(e)}")
        return None, None

def create_app():
    """Tạo và cấu hình ứng dụng Flask"""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-key')
    
    # Đăng ký các route
    register_auth_routes(app)
    register_admin_routes(app)
    register_film_routes(app)
    register_error_handlers(app)
    register_user_routes(app)
    app.register_blueprint(favorite_bp)
    
    # Hàm trợ giúp kiểm tra trạng thái đăng nhập
    def login_required(redirect_url='login'):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để xem trang này', 'error')
            return redirect(url_for(redirect_url))
        return None
    
    # Hàm trợ giúp lấy dữ liệu người dùng
    def get_user_data(user_id):
        client, db = get_db_connection()
        user_data = {
            'username': session.get('username', 'User'),
            'user_id': user_id,
            'registerDate': datetime.now()
        }
        
        try:
            # Thử như ObjectId
            try:
                user = db.users.find_one({'_id': ObjectId(user_id)})
            except:
                try:
                    # Thử như ID số
                    user_id_int = int(user_id)
                    user = db.users.find_one({'id': user_id_int})
                except:
                    user = None
            
            if user:
                user_data = {
                    'username': user.get('username', 'User'),
                    'id': str(user.get('_id')),
                    'fullName': user.get('fullName', ''),
                    'registerDate': user.get('registerDate', datetime.now()),
                    'role': user.get('role', '')
                }
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu người dùng: {str(e)}")
        finally:
            if client:
                client.close()
                
        return user_data
    
    # Trang tài khoản người dùng với danh sách yêu thích
    @app.route('/account')
    def account():
        login_check = login_required()
        if login_check:
            return login_check
        
        user_id = session.get('user_id')
        user_data = get_user_data(user_id)
        favorites = Favorite.get_user_favorite_films(user_id)
        
        return render_template('account.html', favorites=favorites, user=user_data)
    
    # Trang tất cả yêu thích
    @app.route('/favorites')
    def favorites():
        login_check = login_required('home')
        if login_check:
            return login_check
        
        user_id = session.get('user_id')
        films = Favorite.get_user_favorite_films(user_id)
        
        # Lấy top films từ danh sách favorites
        top_films = films[:5] if len(films) >= 5 else films
        
        # Phân trang
        items_per_page = 12
        total_films = len(films)
        total_pages = (total_films // items_per_page) + (1 if total_films % items_per_page != 0 else 0)
        
        page = request.args.get('page', 1, type=int)
        start = (page - 1) * items_per_page
        end = start + items_per_page
        films_on_page = films[start:end]
        
        return render_template('favorites.html', 
                              films=films_on_page,
                              total_pages=total_pages,
                              current_page=page,
                              top_films=top_films)
    
    # API routes cho yêu thích
    @app.route('/user/favorites/check/<film_id>')
    def check_favorite(film_id):
        if 'user_id' not in session:
            return jsonify({"isFavorite": False})
        
        user_id = session.get('user_id')
        is_favorite = Favorite.is_favorite(user_id, film_id)
        return jsonify({"isFavorite": is_favorite})
    
    @app.route('/user/favorites/toggle/<film_id>', methods=['POST'])
    def toggle_favorite(film_id):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = session.get('user_id')
        result, status_code = Favorite.toggle_favorite(user_id, film_id)
        return jsonify(result), status_code
    
    @app.route('/user/favorites')
    def get_favorites_json():
        if 'user_id' not in session:
            return jsonify([])
        
        user_id = session.get('user_id')
        films = Favorite.get_user_favorite_films(user_id)
        return jsonify(films)
    
    # Import debug routes trong môi trường phát triển
    if app.config.get('ENV') == 'development':
        from routes.debug_routes import register_debug_routes
        register_debug_routes(app)
    
    # Khởi tạo kết nối và index MongoDB
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
            
            # Tạo index cho favorites
            try:
                db.favorites.create_index([("user_id", 1), ("film_id", 1)], unique=True)
                db.favorites.create_index("user_id")
                db.favorites.create_index("film_id")
                logger.info("Index favorites được tạo thành công")
            except Exception as e:
                logger.error(f"Lỗi khi tạo index favorites: {str(e)}")
            
            # Đóng kết nối
            client.close()
            logger.info(f"Kết nối MongoDB được khởi tạo cho cơ sở dữ liệu: {db_name}")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo MongoDB: {str(e)}")
    
    return app

app = create_app()

if __name__ == '__main__':
    try:
        os.makedirs('logs', exist_ok=True)
    except Exception as e:
        logger.error(f"Lỗi khi tạo thư mục: {str(e)}")
    
    app.run(debug=True)

