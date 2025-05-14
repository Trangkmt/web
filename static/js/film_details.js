document.addEventListener('DOMContentLoaded', function() {
    // Lấy tham chiếu các phần tử DOM
    const favoriteBtn = document.getElementById('favorite-btn');
    const heartIcon = document.getElementById('heart-icon');
    const favoriteText = document.getElementById('favorite-text');
    
    // Phần tử của các modal
    const loginModal = document.getElementById('login-modal');
    const registerModal = document.getElementById('register-modal');
    const detailsLoginBtn = document.getElementById('details-login-btn');
    const closeButtons = document.querySelectorAll('.close');
    
    // Form elements
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const registerForm = document.getElementById('register-form');
    const registerError = document.getElementById('register-error');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    
    // Kiểm tra đăng nhập
    const isUserLoggedIn = document.body.classList.contains('logged-in') || 
                          (document.cookie.indexOf('user_id') !== -1) ||
                          (typeof session !== 'undefined' && session.user_id);
    
    // Chuyển đổi nút đăng nhập thành nút yêu thích nếu đã đăng nhập
    if (isUserLoggedIn && detailsLoginBtn) {
        convertLoginToFavoriteBtn();
    }
    
    // Hiển thị thông báo với fallback khi AppNotification chưa load
    function showToast(message, type = 'success') {
        if (typeof AppNotification !== 'undefined') {
            AppNotification.show(message, type);
            return;
        }
        
        // Tạo container thông báo nếu chưa có
        let toastContainer = document.querySelector('.notification-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'notification-container';
            document.body.appendChild(toastContainer);
        }
        
        // Tạo thông báo
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Tạo icon và nội dung thông báo
        const icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.innerHTML = type === 'success' ? '✓' : '⚠';
        
        const text = document.createElement('span');
        text.className = 'toast-message';
        text.textContent = message;
        
        // Gắn các phần tử
        toast.appendChild(icon);
        toast.appendChild(text);
        toastContainer.appendChild(toast);
        
        // Tự động ẩn sau 3 giây
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toastContainer.contains(toast)) {
                    toastContainer.removeChild(toast);
                }
            }, 500);
        }, 3000);
    }
    
    // Modal functionality
    if (detailsLoginBtn) {
        detailsLoginBtn.addEventListener('click', () => loginModal.style.display = 'flex');
    }
    
    // Đóng modal
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            loginModal.style.display = 'none';
            if (registerModal) registerModal.style.display = 'none';
        });
    });
    
    // Đóng modal khi click bên ngoài
    window.addEventListener('click', (event) => {
        if (event.target === loginModal) loginModal.style.display = 'none';
        if (registerModal && event.target === registerModal) registerModal.style.display = 'none';
    });
    
    // Chuyển đổi giữa modal đăng nhập và đăng ký
    if (showRegisterLink) {
        showRegisterLink.addEventListener('click', function(e) {
            e.preventDefault();
            loginModal.style.display = 'none';
            registerModal.style.display = 'flex';
        });
    }
    
    if (showLoginLink) {
        showLoginLink.addEventListener('click', function(e) {
            e.preventDefault();
            registerModal.style.display = 'none';
            loginModal.style.display = 'flex';
        });
    }
    
    // Chuyển đổi nút đăng nhập thành nút yêu thích
    function convertLoginToFavoriteBtn() {
        const detailsLoginBtn = document.getElementById('details-login-btn');
        if (!detailsLoginBtn) return;
        
        const filmId = detailsLoginBtn.getAttribute('data-film-id') || 
                      window.location.pathname.split('/').pop();
        
        // Tạo nút yêu thích mới
        const newFavBtn = document.createElement('button');
        newFavBtn.className = 'add-to-list-btn';
        newFavBtn.id = 'favorite-btn';
        newFavBtn.setAttribute('data-film-id', filmId);
        newFavBtn.innerHTML = '<i class="fas fa-heart" id="heart-icon"></i> <span id="favorite-text">THÊM VÀO YÊU THÍCH</span>';
        
        // Thay thế nút đăng nhập
        detailsLoginBtn.parentNode.replaceChild(newFavBtn, detailsLoginBtn);
        
        // Gắn sự kiện cho nút yêu thích
        newFavBtn.addEventListener('click', toggleFavorite);
        
        // Kiểm tra trạng thái yêu thích
        checkFavoriteStatus(filmId, newFavBtn);
    }
    
    // Kiểm tra trạng thái yêu thích
    function checkFavoriteStatus(filmId, btnElement) {
        fetch(`/user/favorites/check/${filmId}`)
            .then(response => response.json())
            .then(data => {
                if (data.isFavorite) {
                    updateFavoriteButton(btnElement || favoriteBtn, true);
                }
            })
            .catch(error => console.error('Error checking favorite status:', error));
    }
    
    // Cập nhật trạng thái nút yêu thích
    function updateFavoriteButton(btn, isFavorite) {
        if (!btn) return;
        
        const heartIcon = btn.querySelector('.fa-heart') || document.getElementById('heart-icon');
        const favoriteText = btn.querySelector('span') || document.getElementById('favorite-text');
        
        if (isFavorite) {
            btn.classList.add('favorited');
            if (heartIcon) heartIcon.style.color = '#fff';
            if (favoriteText) favoriteText.textContent = 'ĐÃ YÊU THÍCH';
        } else {
            btn.classList.remove('favorited');
            if (heartIcon) heartIcon.style.color = '';
            if (favoriteText) favoriteText.textContent = 'THÊM VÀO YÊU THÍCH';
        }
    }
    
    // Chuyển đổi trạng thái yêu thích
    function toggleFavorite() {
        const btn = this;
        const filmId = btn.getAttribute('data-film-id');
        
        fetch(`/user/favorites/toggle/${filmId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.action === 'added') {
                updateFavoriteButton(btn, true);
                showToast('Đã thêm vào danh sách yêu thích');
            } else if (data.action === 'removed') {
                updateFavoriteButton(btn, false);
                showToast('Đã xóa khỏi danh sách yêu thích');
            } else {
                showToast('Có lỗi xảy ra', 'error');
            }
        })
        .catch(error => {
            console.error('Error toggling favorite:', error);
            showToast('Có lỗi xảy ra khi cập nhật', 'error');
        });
    }
    
    // Chuyển nút yêu thích thành nút đăng nhập
    function convertFavoriteToLoginBtn() {
        const favoriteBtn = document.getElementById('favorite-btn');
        if (!favoriteBtn) return;
        
        const filmId = favoriteBtn.getAttribute('data-film-id') || 
                      window.location.pathname.split('/').pop();
        
        // Tạo nút đăng nhập mới
        const newLoginBtn = document.createElement('button');
        newLoginBtn.className = 'add-to-list-btn login-btn';
        newLoginBtn.id = 'details-login-btn';
        newLoginBtn.setAttribute('data-film-id', filmId);
        newLoginBtn.innerHTML = '<i class="fas fa-heart"></i> ĐĂNG NHẬP';
        
        // Thay thế nút yêu thích
        favoriteBtn.parentNode.replaceChild(newLoginBtn, favoriteBtn);
        
        // Gắn sự kiện cho nút đăng nhập
        newLoginBtn.addEventListener('click', () => loginModal.style.display = 'flex');
    }
    
    // Export funcs to global scope
    window.convertLoginToFavoriteBtn = convertLoginToFavoriteBtn;
    window.convertFavoriteToLoginBtn = convertFavoriteToLoginBtn;
    
    // Xử lý nút yêu thích
    if (favoriteBtn) {
        const filmId = favoriteBtn.getAttribute('data-film-id');
        checkFavoriteStatus(filmId);
        favoriteBtn.addEventListener('click', toggleFavorite);
    }
    
    // Xử lý form đăng nhập
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            loginError.style.display = 'none';
            
            const formData = new FormData(loginForm);
            
            fetch('/auth/login', {
                method: 'POST',
                body: formData,
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loginModal.style.display = 'none';
                    showToast('Đăng nhập thành công!');
                    convertLoginToFavoriteBtn();
                    
                    if (data.username && window.updateUIAfterLogin) {
                        window.updateUIAfterLogin(data.username);
                    }
                    
                    document.body.classList.add('logged-in');
                } else {
                    loginError.textContent = data.message || 'Đăng nhập thất bại!';
                    loginError.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Login error:', error);
                loginError.textContent = 'Lỗi kết nối! Vui lòng thử lại sau.';
                loginError.style.display = 'block';
            });
        });
    }
    
    // Xử lý form đăng ký
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            registerError.style.display = 'none';
            
            const formData = new FormData(registerForm);
            const password = formData.get('password');
            const confirmPassword = formData.get('confirm-password');
            
            if (password !== confirmPassword) {
                registerError.textContent = 'Mật khẩu không khớp!';
                registerError.style.display = 'block';
                return;
            }
            
            fetch('/auth/register', {
                method: 'POST',
                body: formData,
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    registerModal.style.display = 'none';
                    showToast('Đăng ký thành công!');
                    convertLoginToFavoriteBtn();
                    
                    if (data.username && window.updateUIAfterLogin) {
                        window.updateUIAfterLogin(data.username);
                    }
                } else {
                    registerError.textContent = data.message || 'Đăng ký thất bại!';
                    registerError.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Registration error:', error);
                registerError.textContent = 'Lỗi kết nối! Vui lòng thử lại sau.';
                registerError.style.display = 'block';
            });
        });
    }
});