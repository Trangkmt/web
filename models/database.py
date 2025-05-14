from flask import Flask
import socket
import threading

def init_database(app):
    """Khởi tạo cơ sở dữ liệu MongoDB với việc tạo index được tối ưu hóa
    
    Chức năng:
    - Import các collection và model cần thiết
    - Tạo các index cho các collection để tối ưu hiệu suất truy vấn
    - Tải thể loại mặc định nếu chưa có
    - Tải dữ liệu phim và kiểm tra trùng lặp ID
    
    Args:
        app: Ứng dụng Flask
        
    Returns:
        bool: True nếu khởi tạo thành công, False nếu có lỗi
    """
    try:
        from . import films_collection, genres_collection, users_collection
        from .genre import Genre
        from .film import Film
        
        print("Kiểm tra các collection trong cơ sở dữ liệu film-users...")
        
        # Tạo tất cả các index trong một khối để giảm số lượng thao tác
        try:
            # Film indexes - kết hợp khi có thể
            try:
                films_collection.create_index([("id", 1)], unique=True)
                print("✅ Index id của phim đã được tạo thành công")
            except Exception as e:
                print(f"Lưu ý: Index id của phim có thể đã tồn tại: {str(e)}")
                
            # Index tìm kiếm văn bản - kiểm tra trước khi tạo
            try:
                # Kiểm tra xem index text đã tồn tại chưa
                index_info = films_collection.index_information()
                text_index_exists = any('text' in str(v.get('key', [])) for v in index_info.values())
                
                if not text_index_exists:
                    films_collection.create_index([("title", "text"), ("description", "text")],
                                               default_language="english")
                    print("✅ Index tìm kiếm văn bản của phim đã được tạo thành công")
                else:
                    print("✅ Index tìm kiếm văn bản đã tồn tại - sử dụng index hiện có")
            except Exception as e:
                print(f"Lưu ý: Lỗi khi xử lý index tìm kiếm văn bản: {str(e)}")
            
            # Genre indexes - kết hợp
            try:
                genres_collection.create_index([("slug", 1)], unique=True)
                genres_collection.create_index([("id", 1)], unique=True)
                print("✅ Index của thể loại đã được tạo thành công")
            except Exception as e:
                print(f"Lưu ý: Index của thể loại có thể đã tồn tại: {str(e)}")
            
            # User indexes
            try:
                users_collection.create_index([("username", 1)], unique=True)
                print("✅ Index username của người dùng đã được tạo thành công")
            except Exception as e:
                print(f"Lưu ý: Index username của người dùng có thể đã tồn tại: {str(e)}")
            
            print("Index MongoDB đã được tạo thành công")
        except Exception as e:
            print(f"Lỗi khi tạo index: {str(e)}")
        
        # Tải thể loại và phim
        if not Genre.get_all():
            Genre.create_default_genres()
        
        Film.load_films_from_database()
        
        # Kiểm tra trùng lặp
        duplicate_ids = Film.find_duplicate_ids()
        if duplicate_ids:
            print(f"CẢNH BÁO: Tìm thấy {len(duplicate_ids)} phim có ID trùng lặp")
            
        print("Cơ sở dữ liệu film-users đã khởi tạo thành công.")
        return True
    except Exception as e:
        app.logger.error(f"Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")
        return False

def create_flask_app(app_type='web'):
    """Tạo và cấu hình ứng dụng Flask
    
    Args:
        app_type (str): Loại ứng dụng cần tạo ('api' hoặc 'web')
    
    Returns:
        Flask: Ứng dụng Flask đã được cấu hình
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    
    # Cấu hình riêng cho từng loại có thể được thêm vào đây
    return app

def create_api_app():
    """Tạo ứng dụng Flask API"""
    return create_flask_app('api')

def create_web_app():
    """Tạo ứng dụng Flask web"""
    return create_flask_app('web')

def check_port(port):
    """Kiểm tra xem cổng có khả dụng không"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except socket.error:
        print(f"Cổng {port} đã được sử dụng.")
        return False
