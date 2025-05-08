from flask import request, jsonify, session
import logging
from functools import wraps

# Create a logger
logger = logging.getLogger(__name__)

# Login required API decorator
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Login required'}), 401  # Trả về lỗi 401 nếu chưa đăng nhập
        return f(*args, **kwargs)  # Tiếp tục thực hiện hàm nếu đã đăng nhập
    return decorated_function

def register_api_routes(app):
    """Register all API routes with the app"""
    
    @app.route('/api/add-favorite', methods=['POST'])
    @api_login_required
    def add_favorite():
        """Add a film to favorites"""
        try:
            user_id = session.get('user_id')
            film_id = request.json.get('film_id')
            
            if not film_id:
                return jsonify({'success': False, 'message': 'Film ID is required'}), 400
            
            # Add to database
            from pymongo import MongoClient
            import os
            
            # Connect to MongoDB
            uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
            dbname = os.environ.get('MONGO_DBNAME', "film-users")
            client = MongoClient(uri)
            db = client[dbname]
            
            # Add to user's favorites
            db.users.update_one(
                {"_id": user_id},
                {"$addToSet": {"favorites": film_id}}
            )
            
            return jsonify({'success': True, 'message': 'Film added to favorites'})
        except Exception as e:
            logger.error(f"Error in add_favorite route: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred'}), 500

    @app.route('/api/remove-favorite', methods=['POST'])
    @api_login_required
    def remove_favorite():
        """Remove a film from favorites"""
        try:
            user_id = session.get('user_id')
            film_id = request.json.get('film_id')
            
            if not film_id:
                return jsonify({'success': False, 'message': 'Film ID is required'}), 400
            
            # Remove from database
            from pymongo import MongoClient
            import os
            
            # Connect to MongoDB
            uri = os.environ.get('MONGO_URI', "mongodb+srv://kiwi:trang%402005@film-users.10h2w59.mongodb.net/?retryWrites=true&w=majority")
            dbname = os.environ.get('MONGO_DBNAME', "film-users")
            client = MongoClient(uri)
            db = client[dbname]
            
            # Remove from user's favorites
            db.users.update_one(
                {"_id": user_id},
                {"$pull": {"favorites": film_id}}
            )
            
            return jsonify({'success': True, 'message': 'Film removed from favorites'})
        except Exception as e:
            logger.error(f"Error in remove_favorite route: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred'}), 500
