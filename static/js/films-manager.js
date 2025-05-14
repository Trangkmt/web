const API_URL = '/admin/films/api';

// Phần tử DOM
const filmTable = document.getElementById('filmTable');
const filmModal = document.getElementById('filmModal');
const deleteModal = document.getElementById('deleteModal');
const modalTitle = document.getElementById('modalTitle');
const filmForm = document.getElementById('filmForm');
const addFilmBtn = document.getElementById('addFilmBtn');
const cancelBtn = document.getElementById('cancelBtn');
const saveBtn = document.getElementById('saveBtn');
const deleteFilmName = document.getElementById('deleteFilmName');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
const closeBtns = document.querySelectorAll('.close');
const searchInput = document.getElementById('searchInput');
const statusFilter = document.getElementById('statusFilter');
const filterBtn = document.getElementById('filterBtn');
const pagination = document.getElementById('pagination');
const genreFilterInput = document.querySelector('.genre-filter-input');

// Cài đặt phân trang
const FILMS_PER_PAGE = 6;
let currentPage = 1;
let totalFilms = 0;
let filteredFilms = [];

// Xóa container thông báo cũ và lớp phủ loading
if (document.getElementById('notification-container')) {
    document.getElementById('notification-container').remove();
}
if (document.getElementById('loading-overlay')) {
    document.getElementById('loading-overlay').remove();
}

// Hàm hiển thị lớp phủ loading
function showLoading() {
    AppNotification.showLoading('Đang tải dữ liệu...');
}

// Hàm ẩn lớp phủ loading
function hideLoading() {
    AppNotification.hideLoading();
}

// Hàm hiển thị thông báo
function showNotification(message, type = 'success') {
    AppNotification.show(message, type);
}

// Hàm cải tiến để xử lý dropdown bộ lọc thể loại
function initGenreFilterDropdown() {
    // Lấy tham chiếu đến các phần tử DOM
    const genreFilterInput = document.querySelector('.genre-filter-input');
    const genreFilterCheckboxes = document.querySelector('.genre-filter-checkboxes');
    
    // Hiển thị/ẩn dropdown khi click vào input - Mở/đóng danh sách thể loại
    genreFilterInput.addEventListener('click', (e) => {
        e.stopPropagation(); // Ngăn sự kiện click lan ra ngoài
        genreFilterCheckboxes.classList.toggle('active'); // Thêm/xóa class active
    });
    
    // Ngăn dropdown đóng lại khi click vào bên trong nó - Cho phép chọn nhiều thể loại mà không bị đóng dropdown
    genreFilterCheckboxes.addEventListener('click', (e) => {
        e.stopPropagation(); // Ngăn sự kiện click lan ra ngoài
    });
    
    // Đóng dropdown khi click bên ngoài - Cải thiện trải nghiệm người dùng
    document.addEventListener('click', () => {
        genreFilterCheckboxes.classList.remove('active'); // Ẩn dropdown khi click ra ngoài
    });
    
    // Khởi tạo các trình xử lý sự kiện thay đổi checkbox - Cập nhật hiển thị ngay khi chọn/bỏ chọn thể loại
    const checkboxes = document.querySelectorAll('input[name="filterCategories"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            e.stopPropagation(); // Ngăn sự kiện lan ra khỏi checkbox
            updateSelectedGenresDisplay(); // Cập nhật hiển thị thể loại đã chọn
        });
    });
}

// Cập nhật hiển thị thể loại đã chọn
function updateSelectedGenresDisplay() {
    const selectedGenres = Array.from(document.querySelectorAll('input[name="filterCategories"]:checked'));
    const genreFilterInput = document.querySelector('.genre-filter-input');
    
    if (selectedGenres.length === 0) {
        genreFilterInput.textContent = 'Chọn thể loại';
    } else if (selectedGenres.length === 1) {
        genreFilterInput.textContent = selectedGenres[0].nextElementSibling.textContent.trim();
    } else {
        genreFilterInput.textContent = `${selectedGenres.length} thể loại đã chọn`;
    }
}

// Khởi tạo dropdown bộ chọn thể loại
function initGenreSelectDropdown() {
    const genreSelectInput = document.getElementById('genreSelectInput');
    const genreCheckboxes = document.getElementById('genreCheckboxes');
    
    if (!genreSelectInput || !genreCheckboxes) return;
    
    // Chuyển đổi dropdown khi nhấp vào input
    genreSelectInput.addEventListener('click', (e) => {
        e.stopPropagation();
        genreCheckboxes.classList.toggle('active');
    });
    
    // Ngăn dropdown đóng khi nhấp vào bên trong
    genreCheckboxes.addEventListener('click', (e) => {
        e.stopPropagation();
    });
    
    // Đóng dropdown khi nhấp vào bên ngoài
    document.addEventListener('click', () => {
        genreCheckboxes.classList.remove('active');
    });
    
    // Cập nhật hiển thị thể loại đã chọn khi checkbox thay đổi
    const checkboxes = document.querySelectorAll('input[name="filmCategories"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateSelectedGenresDisplay();
        });
    });
}

// Cập nhật hiển thị thể loại dựa trên checkbox được chọn
function updateSelectedGenresDisplay() {
    const genreSelectInput = document.getElementById('genreSelectInput');
    if (!genreSelectInput) return;
    
    const selectedGenres = Array.from(document.querySelectorAll('input[name="filmCategories"]:checked'));
    
    if (selectedGenres.length === 0) {
        genreSelectInput.textContent = 'Chọn thể loại';
    } else if (selectedGenres.length === 1) {
        const genreName = selectedGenres[0].parentElement.textContent.trim();
        genreSelectInput.textContent = genreName;
    } else {
        genreSelectInput.textContent = `${selectedGenres.length} thể loại đã chọn`;
    }
}

// Hiển thị danh sách phim với phân trang
function displayFilms(films) {
    const tbody = filmTable.querySelector('tbody');
    tbody.innerHTML = '';

    // Tính toán chỉ số bắt đầu và kết thúc của phim trên trang hiện tại
    const startIndex = (currentPage - 1) * FILMS_PER_PAGE;
    const endIndex = startIndex + FILMS_PER_PAGE;
    const filmsToDisplay = films.slice(startIndex, endIndex);

    filmsToDisplay.forEach(film => {
        const genres = film.genres.map(g => g.name).join(', ');
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${film.id}</td>
            <td><img src="${film.poster_path}" alt="${film.title}" class="film-thumbnail"></td>
            <td>
                <div>${film.title}</div>
            </td>
            <td>${genres}</td>
            <td>${film.episode_count || 'N/A'}</td>
            <td>${film.release_year || 'N/A'}</td>
            <td><span class="status-badge ${film.status === 'single' ? 'status-single' : 'status-series'}">${film.status === 'single' ? 'Phim lẻ' : 'Phim bộ'}</span></td>
            <td class="action-buttons">
                <button class="action-btn edit-btn" data-id="${film.id}"><i class="fas fa-edit"></i></button>
                <button class="action-btn delete-btn" data-id="${film.id}"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Cập nhật phân trang
    updatePagination(films.length);

    // Thêm event listeners cho các nút
    addEditButtonListeners();
    addDeleteButtonListeners();
}

// Cập nhật phân trang
function updatePagination(total) {
    totalFilms = total;
    const totalPages = Math.ceil(totalFilms / FILMS_PER_PAGE);
    pagination.innerHTML = '';

    // Nút Previous
    const prevBtn = document.createElement('button');
    prevBtn.className = 'btn-page';
    prevBtn.innerHTML = '<i class="fas fa-angle-left"></i>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            displayFilms(filteredFilms);
        }
    });
    pagination.appendChild(prevBtn);

    // Các nút số trang
    for (let i = 1; i <= totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = `btn-page ${i === currentPage ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.addEventListener('click', () => {
            currentPage = i;
            displayFilms(filteredFilms);
        });
        pagination.appendChild(pageBtn);
    }

    // Nút Next
    const nextBtn = document.createElement('button');
    nextBtn.className = 'btn-page';
    nextBtn.innerHTML = '<i class="fas fa-angle-right"></i>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            displayFilms(filteredFilms);
        }
    });
    pagination.appendChild(nextBtn);
}

// Lọc phim theo tiêu đề, thể loại, trạng thái
async function applyFilters() {
    try {
        showLoading();
        
        // Lấy giá trị bộ lọc
        const searchText = searchInput.value.toLowerCase().trim();
        const selectedGenres = Array.from(document.querySelectorAll('input[name="filterCategories"]:checked')).map(checkbox => checkbox.value);
        const selectedStatus = statusFilter.value;
        
        // Build URL with query parameters
        let apiUrl = `${API_URL}/films?`;
        
        // Add title search parameter
        if (searchText) {
            apiUrl += `title=${encodeURIComponent(searchText)}&`;
        }
        
        // Add genre parameters
        selectedGenres.forEach(genre => {
            apiUrl += `genre=${encodeURIComponent(genre)}&`;
        });
        
        // Add status parameter
        if (selectedStatus) {
            apiUrl += `status=${encodeURIComponent(selectedStatus)}`;
        }
        
        // Fetch filtered data from API
        const response = await fetch(apiUrl);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch films: ${response.status} - ${errorText}`);
        }
        
        const films = await response.json();
        
        // Update the filteredFilms array with server-side filtered results
        filteredFilms = films;
        
        // Reset về trang 1 sau khi lọc
        currentPage = 1;
        displayFilms(filteredFilms);
        
        // Show success notification
        if (searchText || selectedGenres.length > 0 || selectedStatus) {
            showNotification(`Đã lọc ${films.length} phim thành công`);
        } else {
            showNotification(`Đã tải ${films.length} phim`);
        }
    } catch (error) {
        console.error('Error applying filters:', error);
        showNotification(`Không thể áp dụng bộ lọc: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Thêm event listeners cho nút Edit
function addEditButtonListeners() {
    const editButtons = document.querySelectorAll('.edit-btn');
    editButtons.forEach(button => {
        button.addEventListener('click', () => {
            const filmId = parseInt(button.getAttribute('data-id'));
            openEditModal(filmId);
        });
    });
}

// Thêm event listeners cho nút Delete
function addDeleteButtonListeners() {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', () => {
            const filmId = parseInt(button.getAttribute('data-id'));
            openDeleteModal(filmId);
        });
    });
}

// Mở modal thêm phim mới
function openAddModal() {
    modalTitle.textContent = 'Thêm Phim Mới';
    filmForm.reset();
    document.getElementById('filmId').value = '';
    document.getElementById('filmPosterUrl').value = '';
    document.getElementById('filmSourceFilm').value = '';
    document.getElementById('imagePreview').innerHTML = '';
    // Reset tất cả checkbox
    const checkboxes = document.querySelectorAll('input[name="filmCategories"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Reset genre display
    if (document.getElementById('genreSelectInput')) {
        document.getElementById('genreSelectInput').textContent = 'Chọn thể loại';
    }
    
    filmModal.style.display = 'block';
}

// Mở modal chỉnh sửa phim
async function openEditModal(filmId) {
    try {
        showLoading();
        const response = await fetch(`${API_URL}/films/${filmId}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch film: ${response.status} - ${errorText}`);
        }
        const film = await response.json();
        
        modalTitle.textContent = 'Chỉnh Sửa Phim';
        document.getElementById('filmId').value = film.id;
        document.getElementById('filmTitle').value = film.title || '';
        // Set checkboxes
        const checkboxes = document.querySelectorAll('input[name="filmCategories"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = film.genre_ids && film.genre_ids.includes(parseInt(checkbox.value));
        });
        document.getElementById('filmEpisodes').value = film.episode_count || '';
        document.getElementById('filmReleaseYear').value = film.release_year || '';
        document.getElementById('filmStatus').value = film.status || 'single';
        document.getElementById('filmPosterUrl').value = film.poster_path || '';
        document.getElementById('filmSourceFilm').value = film.source_film || '';
        document.getElementById('filmDescription').value = film.description || '';
        
        // Update genre display
        updateSelectedGenresDisplay();
        
        const imagePreview = document.getElementById('imagePreview');
        if (film.poster_path) {
            imagePreview.innerHTML = `<img src="${film.poster_path}" alt="${film.title}">`;
        } else {
            imagePreview.innerHTML = '';
        }
        
        filmModal.style.display = 'block';
        showNotification(`Đã tải thông tin phim "${film.title}"`);
    } catch (error) {
        console.error('Error fetching film:', error);
        showNotification(`Không thể tải thông tin phim: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Mở modal xác nhận xóa
async function openDeleteModal(filmId) {
    try {
        showLoading();
        const response = await fetch(`${API_URL}/films/${filmId}`);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch film: ${response.status} - ${errorText}`);
        }
        const film = await response.json();
        
        deleteFilmName.textContent = film.title;
        confirmDeleteBtn.setAttribute('data-id', film.id);
        deleteModal.style.display = 'block';
    } catch (error) {
        console.error('Error fetching film:', error);
        showNotification(`Không thể tải thông tin phim: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Lưu phim
async function saveFilm(event) {
    event.preventDefault();
    
    try {
        showLoading();
        
        const filmId = document.getElementById('filmId').value;
        const title = document.getElementById('filmTitle').value;
        const description = document.getElementById('filmDescription').value;
        const release_year = document.getElementById('filmReleaseYear').value;
        const episode_count = parseInt(document.getElementById('filmEpisodes').value) || 1;
        const status = document.getElementById('filmStatus').value;
        const poster_path = document.getElementById('filmPosterUrl').value || '/static/images/placeholder.jpg';
        const source_film = document.getElementById('filmSourceFilm').value || '';
        
        // Get selected genres
        const checkboxes = document.querySelectorAll('input[name="filmCategories"]:checked');
        const genre_ids = Array.from(checkboxes).map(checkbox => parseInt(checkbox.value));

        const filmData = {
            title,
            description,
            release_year,
            episode_count,
            poster_path,
            source_film,
            genre_ids,
            status
        };

        const method = filmId ? 'PUT' : 'POST';
        const url = filmId ? `${API_URL}/films/${filmId}` : `${API_URL}/films`;

        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(filmData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to save film: ${response.status}`);
        }

        filmModal.style.display = 'none';
        applyFilters(); // Refresh film list
        
        const action = filmId ? 'cập nhật' : 'thêm mới';
        showNotification(`Đã ${action} phim "${title}" thành công`);
    } catch (error) {
        console.error('Error saving film:', error);
        showNotification(`Lỗi khi lưu phim: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Xóa phim
async function deleteFilm(filmId) {
    try {
        showLoading();
        const filmName = deleteFilmName.textContent;
        
        const response = await fetch(`${API_URL}/films/${filmId}`, { method: 'DELETE' });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to delete film: ${response.status}`);
        }
        deleteModal.style.display = 'none';
        applyFilters(); // Refresh film list
        
        showNotification(`Đã xóa phim "${filmName}" thành công`);
    } catch (error) {
        console.error('Error deleting film:', error);
        showNotification(`Lỗi khi xóa phim: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Xử lý sự kiện khi nhập URL ảnh
document.getElementById('filmPosterUrl').addEventListener('input', function(event) {
    const url = event.target.value;
    const imagePreview = document.getElementById('imagePreview');
    if (url) {
        imagePreview.innerHTML = `<img src="${url}" alt="Preview">`;
    } else {
        imagePreview.innerHTML = '';
    }
});

// Event Listeners
addFilmBtn.addEventListener('click', openAddModal);
filmForm.addEventListener('submit', saveFilm);
cancelBtn.addEventListener('click', () => {
    filmModal.style.display = 'none';
});
confirmDeleteBtn.addEventListener('click', () => {
    const filmId = confirmDeleteBtn.getAttribute('data-id');
    deleteFilm(filmId);
});
cancelDeleteBtn.addEventListener('click', () => {
    deleteModal.style.display = 'none';
});
filterBtn.addEventListener('click', applyFilters);

// Đóng modal khi click vào nút close
closeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        filmModal.style.display = 'none';
        deleteModal.style.display = 'none';
    });
});

// Đóng modal khi click bên ngoài modal
window.addEventListener('click', (event) => {
    if (event.target === filmModal) {
        filmModal.style.display = 'none';
    }
    if (event.target === deleteModal) {
        deleteModal.style.display = 'none';
    }
});

// Hiển thị danh sách phim khi trang được tải
document.addEventListener('DOMContentLoaded', () => {
    // Initialize genre filter dropdown behavior
    initGenreFilterDropdown();
    
    // Initialize selected genres display
    updateSelectedGenresDisplay();
    
    // Initialize genre select dropdown in modal
    initGenreSelectDropdown();
    
    // Load films
    applyFilters();
});