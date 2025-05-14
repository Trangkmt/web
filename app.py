import os
import logging
from flask import Flask, render_template, session
from datetime import datetime

# Import routes
from routes.auth_routes import register_auth_routes
from routes.admin_routes import register_admin_routes
from routes.film_routes import register_film_routes
from routes.error_handlers import register_error_handlers
from routes.user_routes import register_user_routes

# Import models and utilities
from utils.db import initialize_database
from utils.auth_utils import login_required, get_user_data

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

def create_app():
    """Tạo và cấu hình ứng dụng Flask"""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'default-dev-key')
    
    # Đăng ký các route
    register_auth_routes(app)
    register_admin_routes(app)
    register_film_routes(app)
    register_error_handlers(app)
    register_user_routes(app)  # This now includes favorite routes
    
    # Import debug routes trong môi trường phát triển
    if app.config.get('ENV') == 'development':
        from routes.debug_routes import register_debug_routes
        register_debug_routes(app)
    
    return app

# Create application instance
app = create_app()

# Khởi tạo cơ sở dữ liệu khi khởi động
initialize_database()

if __name__ == '__main__':
    try:
        os.makedirs('logs', exist_ok=True)
    except Exception as e:
        logger.error(f"Lỗi khi tạo thư mục: {str(e)}")
    
    app.run(debug=True)

