import logging
from flask import render_template, request, redirect, url_for, current_app, session
from pymongo import MongoClient
import os
from bson import ObjectId

# Use optimized database utilities
from utils.db_utils import (
    get_db_connection, serialize_id, 
    find_film_by_id, get_all_genres, get_top_films
)

logger = logging.getLogger(__name__)

def serialize_id(film):
    """Convert ObjectId to string in film document"""
    # If film is already a dict (serialized), just return it with _id as string
    if isinstance(film, dict):
        # Make a copy of the dictionary to avoid modifying the original
        film_copy = film.copy()
        # Convert ObjectId to string if _id exists
        if '_id' in film_copy and not isinstance(film_copy['_id'], str):
            film_copy['_id'] = str(film_copy['_id'])
        return film_copy
    
    # If film is a MongoDB document or other object, try to convert to dict
    try:
        film_dict = dict(film)
        if '_id' in film_dict and not isinstance(film_dict['_id'], str):
            film_dict['_id'] = str(film_dict['_id'])
        return film_dict
    except (TypeError, ValueError):
        # If conversion fails, return original
        return film

def get_genres():
    """Lấy tất cả thể loại phim từ database với cơ chế cache
    
    Chức năng:
    - Kết nối đến MongoDB thông qua hàm get_db_connection
    - Sử dụng hàm get_all_genres với cache để tối ưu hiệu suất
    - Xử lý lỗi và trả về danh sách trống nếu có vấn đề
    - Không đóng kết nối vì được quản lý bởi connection pool
    
    Returns:
        list: Danh sách các thể loại phim, hoặc danh sách trống nếu có lỗi
    """
    client, db = get_db_connection()
    if db is None:
        return []
    
    try:
        # Sử dụng hàm thể loại có cache
        genres = get_all_genres(db.genres)
        return genres
    except Exception as e:
        logger.error(f"Lỗi khi lấy thể loại phim: {str(e)}")
        return []
    finally:
        # Không cần đóng kết nối - nó được quản lý bởi connection pool
        pass

def register_film_routes(app):
    """Register film-related routes with the Flask application"""
    
    @app.context_processor
    def inject_common_data():
        """Inject common data into all templates"""
        return {
            'genres': get_genres(),
            'session': request.cookies.to_dict()  # Simplified session handling
        }
    
    @app.route('/')
    def home():
        """Homepage route with optimized film loading"""
        client, db = get_db_connection()
        if db is None:
            return render_template('homepage.html', new_films=[], all_films=[], top_films=[])
        
        try:
            # Use projection to limit fields for better performance
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            # Get featured/new films (latest 12)
            new_films = list(db.films.find({}, projection).sort("_id", -1).limit(12))
            
            # Fix: Process each film individually through serialize_id
            serialized_new_films = []
            for film in new_films:
                serialized_new_films.append(serialize_id(film))
            new_films = serialized_new_films
            
            # Get all films for collection section (limit to 16)
            all_films = list(db.films.find({}, projection).limit(16))
            all_films = [serialize_id(film) for film in all_films]
            
            # Get top films by rating (use cached function)
            top_films = get_top_films(db.films, 10)
            top_films = [serialize_id(film) for film in top_films]
            
            return render_template('homepage.html', 
                                  new_films=new_films, 
                                  all_films=all_films, 
                                  top_films=top_films)
        except Exception as e:
            logger.error(f"Error loading homepage: {str(e)}")
            return render_template('error.html', message="Error loading homepage")
    
    @app.route('/film/<int:film_id>')
    def film_details(film_id):
        """Show details for a specific film with optimized loading"""
        client, db = get_db_connection()
        
        # Lấy user_id từ session
        user_id = session.get('user_id')
        is_favorited = False  # Mặc định là chưa yêu thích

        if db is None:
            return render_template('film_details.html', film=None, related_films=[], top_films=[], user_id=user_id)

        try:
            # Get the film by ID with optimized function - ensure episode_count is included
            film = find_film_by_id(db.films, film_id, projection={
                "id": 1, "title": 1, "poster_path": 1, "rating": 1,
                "release_year": 1, "description": 1, "genre_ids": 1,
                "episode_count": 1, "source_film": 1, "views": 1
            })
            
            if not film:
                return render_template('error.html', message="Film not found"), 404
            
            # Check if episode_count is missing and set a default if needed
            if "episode_count" not in film or film["episode_count"] is None:
                film["episode_count"] = 1
                print(f"Warning: Film {film_id} missing episode_count, setting default value 1")
            
            # Serialize film ObjectId
            film = serialize_id(film)
            
            # Add genre names to film object
            if film.get("genre_ids"):
                genre_names = []
                for genre_id in film.get("genre_ids", []):
                    genre = db.genres.find_one({"id": genre_id}, {"name": 1})
                    if genre and genre.get("name"):
                        genre_names.append(genre.get("name"))
                film["genres"] = genre_names
                # Log for debugging
                print(f"Film {film_id} genres: {genre_names}")
            else:
                # Ensure film has genres field even if no genre_ids found
                film["genres"] = []
                print(f"No genre_ids found for film {film_id}")
            
            # Kiểm tra xem người dùng đã yêu thích phim này chưa
            if user_id:
                try:
                    user_id_obj = ObjectId(user_id)
                except:
                    user_id_obj = user_id
                
                favorite = db.favorites.find_one({
                    "user_id": user_id_obj,
                    "film_id": film_id
                })
                is_favorited = favorite is not None
            
            # Get related films (same genre) with projection for speed
            related_films = []
            if film.get("genre_ids"):
                # Use projection to limit fields
                projection = {
                    "id": 1, "title": 1, "poster_path": 1, 
                    "rating": 1, "release_year": 1
                }
                
                related_films = list(db.films.find({
                    "genre_ids": {"$in": film.get("genre_ids", [])},
                    "id": {"$ne": film_id}  # Exclude current film
                }, projection).limit(8))
                
                # Serialize ObjectIds
                related_films = [serialize_id(related) for related in related_films]
            
            # Get top films (use cached function)
            top_films = get_top_films(db.films, 5)
            
            return render_template('film_details.html', 
                                film=film, 
                                related_films=related_films,
                                top_films=top_films,
                                user_id=user_id,
                                is_favorited=is_favorited)
        except Exception as e:
            logger.error(f"Error loading film details for ID {film_id}: {str(e)}")
            return render_template('error.html', message="Error loading film details")
    
    @app.route('/watch/<int:film_id>')
    def watch_film(film_id):
        """Watch a specific film with optimized queries"""
        client, db = get_db_connection()
        if db is None:
            return render_template('play_film.html', film=None, related_films=[], top_films=[])
        
        try:
            # Get the film with optimized function - include ALL fields for video player
            # Don't use projection to ensure we get all fields including video URLs
            film = find_film_by_id(db.films, film_id, projection=None)
            
            if not film:
                return render_template('error.html', message="Film not found"), 404
            
            # Serialize film ObjectId
            film = serialize_id(film)
            
            # Debug logging to trace the problem
            print(f"Film data for ID {film_id}: source_film={film.get('source_film')}")
            
            # Ensure film has video sources
            if not film.get('video_url') and not film.get('source_film'):
                print(f"Warning: Film ID {film_id} ({film.get('title')}) has no video sources")
            
            # Get related films (same genre) with limited fields
            related_films = []
            if film.get("genre_ids"):
                projection = {
                    "id": 1, "title": 1, "poster_path": 1, 
                    "rating": 1, "release_year": 1
                }
                
                related_films = list(db.films.find({
                    "genre_ids": {"$in": film.get("genre_ids", [])},
                    "id": {"$ne": film_id}  # Exclude current film
                }, projection).limit(8))
                
                # Serialize ObjectIds
                related_films = [serialize_id(related) for related in related_films]
            
            # Get top films (use cached function)
            top_films = get_top_films(db.films, 5)
            
            return render_template('play_film.html', 
                                  film=film, 
                                  related_films=related_films,
                                  top_films=top_films)
        except Exception as e:
            logger.error(f"Error loading play film page for ID {film_id}: {str(e)}")
            return render_template('error.html', message="Error loading film player")
    
    @app.route('/collection')
    def collection():
        """Show the film collection with optimized pagination"""
        page = request.args.get('page', 1, type=int)
        per_page = 16  # Films per page
        
        client, db = get_db_connection()
        if db is None:
            return render_template('collection.html', films=[], top_films=[], 
                                  current_page=1, total_pages=1)
        
        try:
            # Calculate skip value for pagination
            skip = (page - 1) * per_page
            
            # Use projection to limit fields for better performance
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1, 
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            # Get films for current page
            films = list(db.films.find({}, projection).skip(skip).limit(per_page))
            
            # Serialize ObjectIds
            films = [serialize_id(film) for film in films]
            
            # Get total count for pagination - use cached aggregation if possible
            total_films = db.films.estimated_document_count()  # Much faster than count_documents
            total_pages = (total_films + per_page - 1) // per_page  # Ceiling division
            
            # Get top films for sidebar (use cached function)
            top_films = get_top_films(db.films, 10)
            
            return render_template('collection.html', 
                                  films=films,
                                  top_films=top_films,
                                  current_page=page,
                                  total_pages=total_pages)
        except Exception as e:
            logger.error(f"Error loading collection page: {str(e)}")
            return render_template('error.html', message="Error loading film collection")
        
    @app.route('/genre/<string:genre_slug>')
    def genre(genre_slug):
        """Show films in a specific genre with optimized queries"""
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Films per page
        
        client, db = get_db_connection()
        if db is None:
            return render_template('film_genres.html', genre_movies=[], top_movies=[],
                                  genre="", genre_slug="", current_page=1, total_pages=1)
        
        try:
            # Get genre by slug - lightweight query
            genre_doc = db.genres.find_one({"slug": genre_slug}, {"id": 1, "name": 1})
            
            if not genre_doc:
                return render_template('error.html', message="Genre not found"), 404
            
            # Calculate skip value for pagination
            skip = (page - 1) * per_page
            
            # Use projection to limit fields for better performance
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1, 
                "release_year": 1, "description": 1
            }
            
            # Get films in this genre
            genre_movies = list(db.films.find({
                "genre_ids": genre_doc["id"]
            }, projection).skip(skip).limit(per_page))
            
            # Serialize ObjectIds
            genre_movies = [serialize_id(movie) for movie in genre_movies]
            
            # Get total count for pagination - use hint for index usage
            total_films = db.films.count_documents({"genre_ids": genre_doc["id"]})
            total_pages = (total_films + per_page - 1) // per_page  # Ceiling division
            
            # Get top films for sidebar (use cached function)
            top_movies = get_top_films(db.films, 7)
            
            return render_template('film_genres.html',
                                  genre_movies=genre_movies,
                                  top_movies=top_movies,
                                  genre=genre_doc["name"],
                                  genre_slug=genre_slug,
                                  current_page=page,
                                  total_pages=total_pages)
        except Exception as e:
            logger.error(f"Error loading genre page for {genre_slug}: {str(e)}")
            return render_template('error.html', message="Error loading genre page")
    
    @app.route('/search')
    def search():
        """Search for films with optimized text search"""
        query = request.args.get('query', '')
        page = request.args.get('page', 1, type=int)
        per_page = 12  # Results per page
        
        if not query:
            return redirect(url_for('home'))
        
        client, db = get_db_connection()
        if db is None:
            return render_template('search_result.html', results=[], suggested_films=[],
                                  query=query, current_page=1, total_pages=1, top_films=[])
        
        try:
            # Calculate skip value for pagination
            skip = (page - 1) * per_page
            
            # Use projection to limit fields for better performance
            projection = {
                "id": 1, "title": 1, "poster_path": 1, "rating": 1, 
                "release_year": 1, "description": 1, "genre_ids": 1
            }
            
            # Always use regex search - more reliable than text search
            logger.info(f"Performing regex search for query: '{query}'")
            return use_regex_search(db, query, projection, skip, per_page, page)
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {str(e)}")
            # Try to return empty results with suggested films as fallback
            try:
                # Get top films for sidebar
                top_films = get_top_films(db.films, 5)
                
                # Get some random films as suggestions
                suggested_films = []
                try:
                    suggested_films = list(db.films.aggregate([
                        {"$sample": {"size": 8}},
                        {"$project": projection}
                    ]))
                    suggested_films = [serialize_id(film) for film in suggested_films]
                except Exception:
                    pass
                
                return render_template('search_result.html',
                                    results=[],
                                    suggested_films=suggested_films,
                                    top_films=top_films,
                                    query=query,
                                    current_page=1,
                                    total_pages=1)
            except:
                return render_template('error.html', message="Error performing search")

    def use_regex_search(db, query, projection, skip, per_page, page):
        """Search using regex - reliable method that works for all query lengths"""
        try:
            # Create regex search query - this is more reliable than text search
            search_query = {
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"description": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Perform the search
            results = list(db.films.find(
                search_query, 
                projection
            ).skip(skip).limit(per_page))
            
            # Get total count for pagination
            total_results = db.films.count_documents(search_query)
            total_pages = max(1, (total_results + per_page - 1) // per_page)  # Ensure at least 1 page
            
            # Get suggested films - use aggregation for random selection
            suggested_films = list(db.films.aggregate([
                {"$sample": {"size": 8}},
                {"$project": projection}
            ]))
            
            # Serialize ObjectIds
            results = [serialize_id(result) for result in results]
            suggested_films = [serialize_id(film) for film in suggested_films]
            
            # Get top films for sidebar
            top_films = get_top_films(db.films, 5)
            
            logger.info(f"Found {len(results)} results for '{query}' using regex search")
            
            return render_template('search_result.html',
                                  results=results,
                                  suggested_films=suggested_films,
                                  top_films=top_films,
                                  query=query,
                                  current_page=page,
                                  total_pages=total_pages)
        except Exception as e:
            logger.error(f"Error in regex search: {str(e)}")
            
            # Return empty results as fallback
            top_films = get_top_films(db.films, 5)
            return render_template('search_result.html',
                                  results=[],
                                  suggested_films=[],
                                  top_films=top_films,
                                  query=query,
                                  current_page=1,
                                  total_pages=1)
