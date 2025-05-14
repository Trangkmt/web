from flask import session, redirect, url_for, flash
from bson.objectid import ObjectId
from datetime import datetime
from utils.db import get_db_connection
import logging

logger = logging.getLogger(__name__)

def login_required(redirect_url='login'):
    """Kiểm tra trạng thái đăng nhập của người dùng
    
    Args:
        redirect_url (str): URL để chuyển hướng nếu chưa đăng nhập
        
    Returns:
        None nếu đã đăng nhập, ngược lại chuyển hướng đến trang đăng nhập
    """
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem trang này', 'error')
        return redirect(url_for(redirect_url))
    return None

def get_user_data(user_id):
    """Lấy thông tin người dùng từ cơ sở dữ liệu
    
    Args:
        user_id: ID của người dùng (string hoặc int)
        
    Returns:
        dict: Thông tin người dùng
    """
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
