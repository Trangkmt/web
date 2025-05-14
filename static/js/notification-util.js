/**
 * Notification utility for the application
 * Provides methods for showing loading indicators, success/error notifications
 */
const AppNotification = {
    // Default durations
    DURATIONS: {
        SHORT: 2000,
        MEDIUM: 3000,
        LONG: 5000
    },
    
    /**
     * Show a notification message
     * @param {string} message - The message to display
     * @param {string} type - The type of notification (success, error, info)
     * @param {number} duration - Duration in ms to show the notification
     */
    show: function(message, type = 'info', duration = this.DURATIONS.MEDIUM) {
        // Clear existing notifications
        this._clearExistingNotifications();

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerText = message;
        
        // Add toast to body
        document.body.appendChild(toast);
        
        // Show toast with animation delay
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Tự động ẩn thông báo sau thời gian quy định
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
            }, 300); // Đợi hiệu ứng mờ dần kết thúc trước khi xóa khỏi DOM
        }, duration);
    },

    /**
     * Show a loading indicator - Hiển thị trạng thái đang tải
     * @param {string} message - Optional message to display with the loading indicator
     */
    showLoading: function(message = 'Đang tải...') {
        // Xóa bỏ overlay tải hiện có để tránh trùng lặp
        this.hideLoading();
        
        // Tạo overlay loading với hiệu ứng quay
        const overlay = this._createLoadingOverlay(message);
        document.body.appendChild(overlay);
    },

    /**
     * Hide the loading indicator - Ẩn trạng thái đang tải
     */
    hideLoading: function() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay && document.body.contains(overlay)) {
            document.body.removeChild(overlay);
        }
    },

    /**
     * Show an error notification with a retry button - Hiển thị thông báo lỗi với nút thử lại
     * @param {string} message - The error message
     * @param {Function} retryCallback - Function to call when retry is clicked
     */
    showErrorWithRetry: function(message, retryCallback) {
        this._clearExistingNotifications();
        
        // Tạo thông báo lỗi với nút thử lại
        const toast = this._createErrorWithRetryToast(message, retryCallback);
        document.body.appendChild(toast);
        
        // Hiệu ứng hiện dần thông báo
        setTimeout(() => toast.classList.add('show'), 100);
    },
    
    // Các phương thức trợ giúp riêng tư
    _clearExistingNotifications: function() {
        // Xóa tất cả thông báo hiện tại để tránh chồng chất
        const existingToasts = document.querySelectorAll('.toast');
        existingToasts.forEach(toast => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        });
    },
    
    _createLoadingOverlay: function(message) {
        // Tạo overlay phủ toàn màn hình với vòng quay loading
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        
        // Sử dụng class CSS hiện có, hoặc tạo style nếu không có
        if (!document.querySelector('link[href*="common.css"]')) {
            // Thêm style tối thiểu cần thiết nếu common.css chưa được tải
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            overlay.style.zIndex = '9999';
        }
        
        // Tạo container chứa spinner và message
        const spinnerContainer = document.createElement('div');
        spinnerContainer.style.textAlign = 'center';
        
        // Tạo phần tử spinner quay tròn
        const spinner = document.createElement('div');
        spinner.className = 'spinner';
        spinnerContainer.appendChild(spinner);
        
        // Tạo phần tử hiển thị thông báo
        const messageEl = document.createElement('p');
        messageEl.textContent = message;
        messageEl.style.marginTop = '15px';
        messageEl.style.color = 'white';
        spinnerContainer.appendChild(messageEl);
        
        overlay.appendChild(spinnerContainer);
        return overlay;
    },
    
    _createErrorWithRetryToast: function(message, retryCallback) {
        const toast = document.createElement('div');
        toast.className = 'toast error';
        toast.style.width = 'auto';
        toast.style.maxWidth = '400px';
        toast.style.display = 'flex';
        toast.style.flexDirection = 'column';
        toast.style.padding = '15px';
        
        const messageElement = document.createElement('div');
        messageElement.innerText = message;
        messageElement.style.marginBottom = '10px';
        toast.appendChild(messageElement);
        
        const retryButton = document.createElement('button');
        retryButton.innerText = 'Thử lại';
        retryButton.style.alignSelf = 'flex-end';
        retryButton.style.padding = '5px 10px';
        retryButton.style.backgroundColor = 'white';
        retryButton.style.color = '#F44336';
        retryButton.style.border = 'none';
        retryButton.style.borderRadius = '3px';
        retryButton.style.cursor = 'pointer';
        
        retryButton.addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (document.body.contains(toast)) {
                    document.body.removeChild(toast);
                }
                if (typeof retryCallback === 'function') {
                    retryCallback();
                }
            }, 300);
        });
        
        toast.appendChild(retryButton);
        return toast;
    }
};