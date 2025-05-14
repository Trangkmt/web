from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from bson.objectid import ObjectId
from functools import wraps
import os
from datetime import datetime
from werkzeug.security import check_password_hash

# Import Favorite model từ module favorite
from models.favorite import Favorite

# Import utils for cleaner authentication handling
from utils.auth_utils import login_required, get_user_data

# Tạo Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/user')

# Hàm kết nối MongoDB
def get_db():
    """Lấy kết nối cơ sở dữ liệu MongoDB"""
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
        print(f"Lỗi kết nối cơ sở dữ liệu: {str(e)}")
        return None, None

# Decorator xác thực
def login_required_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Yêu cầu xác thực"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Hàm hỗ trợ tìm người dùng theo ID
def find_user_by_id(db, user_id):
    try:
        # Thử tìm bằng ObjectId trước
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            return user
            
        # Thử ID số nếu ObjectId không thành công
        user_id_int = int(user_id)
        return db.users.find_one({'id': user_id_int})
    except:
        return None

# Trang hồ sơ người dùng - Improved implementation
@user_bp.route('/account')
def profile():
    login_check = login_required()
    if login_check:
        return login_check
    
    user_id = session.get('user_id')
    user_data = get_user_data(user_id)
    
    return render_template('account.html', user=user_data)

# API routes cho hồ sơ & cập nhật người dùng
@user_bp.route('/profile/data')
@login_required_api
def profile_data():
    """Lấy dữ liệu hồ sơ người dùng dạng JSON"""
    client, db = get_db()
    if db is None:
        return jsonify({
            'username': session.get('username', 'User'),
            'error': 'Kết nối cơ sở dữ liệu thất bại'
        }), 500
    
    try:
        user_id = session.get('user_id')
        user = find_user_by_id(db, user_id)
        
        if not user:
            return jsonify({'error': 'Không tìm thấy người dùng'}), 404
        
        # Chuyển ObjectId thành chuỗi để serialize JSON
        if '_id' in user:
            user['_id'] = str(user['_id'])
        
        # Loại bỏ thông tin nhạy cảm
        if 'password' in user:
            del user['password']
            
        # Format register date
        register_date = user.get('registerDate')
        if register_date:
            if isinstance(register_date, str):
                try:
                    register_date = datetime.fromisoformat(register_date)
                except ValueError:
                    try:
                        register_date = datetime.strptime(register_date, '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        pass
            
            user['registerDate'] = register_date.isoformat() if isinstance(register_date, datetime) else str(register_date)
        
        return jsonify(user)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if client:
            client.close()

# Cập nhật hồ sơ người dùng
@user_bp.route('/account/update', methods=['POST'])
@login_required_api
def update_profile():
    client, db = get_db()
    if db is None:
        return jsonify({'error': 'Kết nối cơ sở dữ liệu thất bại'}), 500
    
    try:
        # Lấy dữ liệu từ request
        data = request.json
        full_name = data.get('fullName', '').strip()
        
        # Lấy người dùng từ session
        user_id = session.get('user_id')
        
        # Tìm và cập nhật người dùng
        update_data = {'updatedAt': datetime.utcnow()}
        if full_name:
            update_data['fullName'] = full_name
        
        # Thử cập nhật bằng ObjectId trước
        try:
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': update_data}
            )
        except:
            # Thử ID số nếu ObjectId không thành công
            try:
                user_id_int = int(user_id)
                result = db.users.update_one(
                    {'id': user_id_int},
                    {'$set': update_data}
                )
            except:
                return jsonify({'message': 'Không tìm thấy người dùng'}), 404
        
        if result.matched_count == 0:
            return jsonify({'message': 'Không tìm thấy người dùng'}), 404
        
        return jsonify({'message': 'Cập nhật hồ sơ thành công'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if client:
            client.close()

# Đổi mật khẩu
@user_bp.route('/password/change', methods=['POST'])
@login_required_api
def change_password():
    client, db = get_db()
    if db is None:
        return jsonify({'error': 'Kết nối cơ sở dữ liệu thất bại'}), 500
    
    try:
        # Lấy dữ liệu từ request
        data = request.json
        current_password = data.get('currentPassword', '').strip()
        new_password = data.get('newPassword', '').strip()
        
        if not current_password or not new_password:
            return jsonify({'message': 'Mật khẩu không được để trống'}), 400
        
        # Lấy người dùng từ session
        user_id = session.get('user_id')
        user = find_user_by_id(db, user_id)
        
        if not user:
            return jsonify({'message': 'Người dùng không tồn tại'}), 404
        
        # Xác thực mật khẩu hiện tại
        stored_password = user.get('password', '')
        password_match = (current_password == stored_password or 
                         check_password_hash(stored_password, current_password))
            
        if not password_match:
            return jsonify({'message': 'Mật khẩu hiện tại không đúng'}), 400
        
        # Cập nhật mật khẩu
        query = {'_id': user['_id']} if isinstance(user.get('_id'), ObjectId) else {'id': user.get('id')}
        update_result = db.users.update_one(
            query,
            {'$set': {'password': new_password, 'updatedAt': datetime.utcnow()}}
        )
        
        if update_result and update_result.matched_count > 0:
            return jsonify({'message': 'Mật khẩu đã được cập nhật thành công'})
        else:
            return jsonify({'message': 'Lỗi khi cập nhật mật khẩu'}), 500
            
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if client:
            client.close()

# ===== FAVORITE ROUTES =====

# Trang xem danh sách phim yêu thích
@user_bp.route('/films/favorites')
def view_favorites():
    login_check = login_required()
    if login_check:
        return login_check
    
    user_id = session.get('user_id')
    
    # Get favorite films using the Favorite model
    films = Favorite.get_user_favorite_films(user_id)
    
    # Only keep films that have valid data
    films = [film for film in films if film]
    
    # Pagination
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
                          current_page=page)

@user_bp.route('/favorites')
@login_required_api
def get_favorites():
    user_id = session.get('user_id')
    films = Favorite.get_user_favorite_films(user_id)
    return jsonify(films)

@user_bp.route('/favorites/check/<film_id>')
@login_required_api
def check_favorite(film_id):
    user_id = session.get('user_id')
    is_favorite = Favorite.is_favorite(user_id, film_id)
    return jsonify({"isFavorite": is_favorite})

@user_bp.route('/favorites/toggle/<film_id>', methods=['POST'])
@login_required_api
def toggle_favorite(film_id):
    user_id = session.get('user_id')
    result, status_code = Favorite.toggle_favorite(user_id, film_id)
    return jsonify(result), status_code

def register_user_routes(app):
    """Đăng ký routes người dùng vào ứng dụng Flask"""
    app.register_blueprint(user_bp)
    
    # Register the main route (non-prefixed version)
    @app.route('/account')
    def account():
        return profile()
        
    @app.route('/films/favorites')
    def films_favorites():
        return view_favorites()
        
    # Register root API paths for backward compatibility
    @app.route('/user/favorites/check/<film_id>')
    def check_favorite_root(film_id):
        if 'user_id' not in session:
            return jsonify({"isFavorite": False})
        user_id = session.get('user_id')
        is_favorite = Favorite.is_favorite(user_id, film_id)
        return jsonify({"isFavorite": is_favorite})
        
    @app.route('/user/favorites/toggle/<film_id>', methods=['POST'])
    def toggle_favorite_root(film_id):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user_id = session.get('user_id')
        result, status_code = Favorite.toggle_favorite(user_id, film_id)
        return jsonify(result), status_code
        
    @app.route('/user/favorites')
    def get_favorites_root():
        if 'user_id' not in session:
            return jsonify([])
        user_id = session.get('user_id')
        films = Favorite.get_user_favorite_films(user_id)
        return jsonify(films)

