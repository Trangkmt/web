from bson.objectid import ObjectId
from functools import lru_cache
from . import films_collection, serialize_id
import time

class Film:
    # Khóa cache cho phim có xếp hạng cao nhất
    _top_rated_cache = {}
    _top_rated_timestamp = 0
    _cache_ttl = 900  # Thời gian cache 15 phút (TTL)
    
    @staticmethod
    def get_all(projection=None):
        """Lấy tất cả phim với xử lý lỗi hiệu quả và projection
        
        Chức năng:
        - Sử dụng projection để giới hạn các trường dữ liệu được trả về
        - Xử lý lỗi và trả về danh sách trống nếu có vấn đề
        - Chuyển đổi ObjectId sang string thông qua serialize_id
        
        Args:
            projection (dict, optional): Chỉ định các trường cần lấy. Mặc định là None.
            
        Returns:
            list: Danh sách phim đã được serialize
        """
        try:
            default_projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1, 
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            projection = projection or default_projection
            results = list(films_collection.find({}, projection))
            return [serialize_id(film) for film in results]
        except Exception as e:
            print(f"Lỗi trong Film.get_all(): {str(e)}")
            return []
    
    @staticmethod
    @lru_cache(maxsize=512)  # Cache lớn hơn cho phim được truy cập thường xuyên
    def get_by_id(film_id, projection=None):
        """Lấy phim theo ID với caching và hiệu suất cải thiện
        
        Chức năng:
        - Sử dụng lru_cache để cache kết quả truy vấn thường xuyên
        - Kiểm tra ID dưới dạng số trước (trường hợp phổ biến nhất)
        - Thử với ObjectId nếu ID số không tìm thấy
        - Sử dụng projection để giới hạn dữ liệu trả về, tối ưu băng thông
        
        Args:
            film_id: ID của phim (số nguyên hoặc chuỗi)
            projection (dict, optional): Chỉ định các trường cần lấy
            
        Returns:
            dict: Thông tin phim đã được serialize, hoặc None nếu không tìm thấy
        """
        default_projection = {
            "_id": 1, "id": 1, "title": 1, "poster_path": 1, 
            "description": 1, "rating": 1, "genre_ids": 1, 
            "release_year": 1, "video_url": 1, "length": 1
        }
        
        projection = projection or default_projection
        
        # Thử ID số trước để tối ưu hóa
        if isinstance(film_id, int) or (isinstance(film_id, str) and film_id.isdigit()):
            film_id_int = int(film_id) if isinstance(film_id, str) else film_id
            film = films_collection.find_one({"id": film_id_int}, projection)
            if film:
                return serialize_id(film)
        
        # Thử ObjectId nếu ID số không thành công
        if isinstance(film_id, str):
            try:
                film = films_collection.find_one({"_id": ObjectId(film_id)}, projection)
                return serialize_id(film) if film else None
            except:
                pass
        
        return None
    
    @staticmethod
    def get_by_genre(genre_id, limit=20, skip=0, projection=None):
        """Lấy phim theo ID thể loại với phân trang và projection
        
        Chức năng:
        - Hỗ trợ phân trang với thông số limit và skip
        - Sử dụng projection để giới hạn dữ liệu trả về
        - Xử lý lỗi và trả về danh sách trống nếu có vấn đề
        
        Args:
            genre_id: ID của thể loại phim
            limit (int): Số lượng phim tối đa trả về, mặc định 20
            skip (int): Số phim bỏ qua (cho phân trang), mặc định 0
            projection (dict, optional): Chỉ định các trường cần lấy
            
        Returns:
            list: Danh sách phim thuộc thể loại đã được serialize
        """
        try:
            default_projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1, 
                "release_year": 1, "description": 1
            }
            
            projection = projection or default_projection
            
            films = films_collection.find({"genre_ids": genre_id}, projection).skip(skip).limit(limit)
            return [serialize_id(film) for film in films]
        except Exception as e:
            print(f"Lỗi trong Film.get_by_genre(): {str(e)}")
            return []
    
    @staticmethod
    def create(data):
        """Tạo phim mới với ID tự động tăng
        
        Chức năng:
        - Tự động tạo ID nếu không được cung cấp
        - Tìm ID lớn nhất hiện có và tăng thêm 1 để tạo ID mới
        - Lưu phim vào database và trả về phim đã được tạo với ID
        
        Args:
            data (dict): Dữ liệu phim cần tạo
            
        Returns:
            dict: Phim đã được tạo với ID và _id đã serialize
        """
        # Tạo ID mới nếu không được cung cấp
        if 'id' not in data:
            max_id = films_collection.find_one(sort=[("id", -1)])
            data['id'] = 1 if max_id is None else max_id.get('id', 0) + 1
        result = films_collection.insert_one(data)
        return serialize_id({**data, "_id": result.inserted_id})
    
    @staticmethod
    def update(film_id, data):
        """Cập nhật phim theo ID số hoặc ObjectId
        
        Chức năng:
        - Hỗ trợ cập nhật theo ID số hoặc ObjectId
        - Tự động xóa cache phim sau khi cập nhật
        - Trả về phim đã cập nhật sau khi hoàn thành
        
        Args:
            film_id: ID của phim (số nguyên hoặc chuỗi)
            data (dict): Dữ liệu phim cần cập nhật
            
        Returns:
            dict: Phim đã cập nhật, hoặc None nếu không tìm thấy
        """
        # Xử lý ID số
        if isinstance(film_id, int) or (isinstance(film_id, str) and film_id.isdigit()):
            film_id_int = int(film_id) if isinstance(film_id, str) else film_id
            films_collection.update_one({"id": film_id_int}, {"$set": data})
            
            # Xóa cache cho phim này
            Film.get_by_id.cache_clear()
            return Film.get_by_id(film_id_int)
        
        # Xử lý ObjectId
        try:
            films_collection.update_one({"_id": ObjectId(film_id)}, {"$set": data})
            
            # Xóa cache cho phim này
            Film.get_by_id.cache_clear()
            return Film.get_by_id(film_id)
        except:
            return None
    
    @staticmethod
    def delete(film_id):
        """Delete a film by either numeric ID or ObjectId"""
        # Handle numeric ID
        if isinstance(film_id, int) or (isinstance(film_id, str) and film_id.isdigit()):
            film_id_int = int(film_id) if isinstance(film_id, str) else film_id
            films_collection.delete_one({"id": film_id_int})
        else:
            # Handle ObjectId
            try:
                films_collection.delete_one({"_id": ObjectId(film_id)})
            except:
                pass
        
        # Clear cache for this film
        Film.get_by_id.cache_clear()
    
    @staticmethod
    def search(query, limit=20, skip=0):
        """Search films with optimized query strategy and fallback"""
        try:
            # Projection to limit fields for better performance
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            # Use text search for longer queries (more efficient)
            if len(query) > 3:
                try:
                    search_query = {"$text": {"$search": query}}
                    projection_with_score = dict(projection)
                    projection_with_score["score"] = {"$meta": "textScore"}
                    
                    films = films_collection.find(
                        search_query, 
                        projection_with_score
                    ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
                    
                    # Convert to list to execute the query and catch any errors
                    films_list = list(films)
                    return [serialize_id(film) for film in films_list]
                except Exception as text_search_error:
                    print(f"Text search failed, falling back to regex: {str(text_search_error)}")
                    # Fall back to regex search if text search fails
                    search_query = {
                        "$or": [
                            {"title": {"$regex": query, "$options": "i"}},
                            {"description": {"$regex": query, "$options": "i"}}
                        ]
                    }
                    films = films_collection.find(search_query, projection).skip(skip).limit(limit)
                    return [serialize_id(film) for film in films]
            else:
                # Use regex for short queries
                search_query = {
                    "$or": [
                        {"title": {"$regex": query, "$options": "i"}},
                        {"description": {"$regex": query, "$options": "i"}}
                    ]
                }
                films = films_collection.find(search_query, projection).skip(skip).limit(limit)
                return [serialize_id(film) for film in films]
        except Exception as e:
            print(f"Error in Film.search(): {str(e)}")
            return []
    
    @staticmethod
    def get_featured(limit=12):
        """Get featured films with projection and caching"""
        try:
            # Projection to limit fields 
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            results = list(films_collection.find(
                {"featured": True}, 
                projection
            ).limit(limit))
            
            return [serialize_id(film) for film in results]
        except Exception as e:
            print(f"Error in Film.get_featured(): {str(e)}")
            return []
    
    @staticmethod
    def get_top_rated(limit=10):
        """Get top rated films with efficient time-based caching"""
        current_time = time.time()
        
        # Return from cache if valid
        if (Film._top_rated_timestamp > 0 and 
            (current_time - Film._top_rated_timestamp) < Film._cache_ttl and
            limit in Film._top_rated_cache):
            return Film._top_rated_cache[limit]
            
        try:
            # Projection to limit fields 
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            # Get more films than needed for cache
            max_cache_size = max(20, limit * 2)
            results = list(films_collection.find(
                {}, 
                projection
            ).sort("rating", -1).limit(max_cache_size))
            
            serialized_results = [serialize_id(film) for film in results]
            
            # Cache the results
            Film._top_rated_cache[limit] = serialized_results[:limit]
            Film._top_rated_timestamp = current_time
            
            return Film._top_rated_cache[limit]
        except Exception as e:
            print(f"Error in Film.get_top_rated(): {str(e)}")
            return []
    
    @staticmethod
    def paginate(page=1, per_page=10, filters=None, projection=None):
        """Paginate films with optimized query and projection"""
        try:
            skip = (page - 1) * per_page
            
            # Default projection
            default_projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            projection = projection or default_projection
            query = filters if filters else {}
            
            # Get total count for pagination
            # Use estimated count for better performance if no filters
            if not filters:
                total_count = films_collection.estimated_document_count()
            else:
                total_count = films_collection.count_documents(query)
                
            total_pages = (total_count + per_page - 1) // per_page
            
            # Get paginated results
            films = films_collection.find(query, projection).skip(skip).limit(per_page)
            
            return {
                "films": [serialize_id(film) for film in films],
                "total_pages": total_pages,
                "total_count": total_count,
                "current_page": page
            }
        except Exception as e:
            print(f"Error in Film.paginate(): {str(e)}")
            return {
                "films": [],
                "total_pages": 1,
                "total_count": 0,
                "current_page": page
            }
    
    @staticmethod
    def load_films_from_database():
        """Get films directly from MongoDB film-users database"""
        try:
            # Use estimated count for better performance
            films_count = films_collection.estimated_document_count()
            if films_count > 0:
                print(f"Found {films_count} films in film-users database.")
                return True
                
            print("No films found in film-users database. Please populate the database.")
            return False
        except Exception as e:
            print(f"Error loading films from database: {str(e)}")
            return False
    
            # Primary indexes
