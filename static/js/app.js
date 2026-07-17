/**
 * Main Application Scripts - NGO Volunteer Management System
 * Handles theme toggling, sidebar, toasts, and UI initialization.
 */

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initSidebar();
    initBootstrapComponents();
    populateNavbar();
    populateSidebarBadges();
    initNotifications();
});

// --- User Navbar Data ---
async function populateNavbar() {
    const navName = document.getElementById('navUserName');
    const navRole = document.getElementById('navUserRole');
    const navAvatar = document.getElementById('navAvatar');
    
    if (!navName || !navRole || !navAvatar) return;

    try {
        const isAdmin = window.location.pathname.startsWith('/admin');
        const endpoint = isAdmin ? '/api/admin/auth/me' : '/api/auth/me';
        const tokenKey = isAdmin ? 'admin_access_token' : 'access_token';
        const token = localStorage.getItem(tokenKey) || '';

        const res = await (window.api ? window.api.get(endpoint.replace('/api', '')) : fetch(endpoint, {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => r.json()));
        
        const data = window.api ? res.data : res;
        if (data.status === 'success' && data.data) {
            const user = data.data.admin || data.data.user || data.data;
            navName.textContent = user.name || user.full_name || 'Admin';
            navRole.textContent = user.role ? user.role.replace('_', ' ') : (isAdmin ? 'Admin' : 'Volunteer');
            
            navAvatar.src = user.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(navName.textContent)}&background=random`;
            navAvatar.classList.remove('d-none');
        }
    } catch (e) {
        console.error("Failed to load navbar user data:", e);
    }
}

// --- Sidebar Badges ---
async function populateSidebarBadges() {
    const requestsBadge = document.getElementById('sidebarRequestsBadge');
    if (!requestsBadge) return;
    
    // Check if we are on admin side
    const isAdmin = window.location.pathname.startsWith('/admin');
    if (isAdmin) {
        try {
            const token = localStorage.getItem('admin_access_token') || '';
            const res = await (window.api ? window.api.get('/dashboard/sidebar-stats') : fetch('/api/dashboard/sidebar-stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            }).then(r => r.json()));
            
            const data = window.api ? res.data : res;
            if (data.status === 'success' && data.data) {
                const count = data.data.pending_requests || 0;
                if (count > 0) {
                    requestsBadge.textContent = count;
                    requestsBadge.classList.remove('d-none');
                } else {
                    requestsBadge.classList.add('d-none');
                }
            }
        } catch (e) {
            console.error("Failed to load sidebar badges:", e);
        }
    }
}

// --- Theme Management (Light/Dark Mode) ---

function initTheme() {
    const themeToggle = document.getElementById("theme-toggle");
    if (!themeToggle) return;

    // Check local storage or system preference
    const storedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    
    let currentTheme = storedTheme || (prefersDark ? "dark" : "light");
    setTheme(currentTheme);

    themeToggle.addEventListener("click", () => {
        currentTheme = currentTheme === "dark" ? "light" : "dark";
        setTheme(currentTheme);
    });
}

function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    
    // Update toggle icon if it exists
    const icon = document.querySelector("#theme-toggle i");
    if (icon) {
        if (theme === "dark") {
            icon.classList.remove("bi-moon");
            icon.classList.add("bi-sun");
        } else {
            icon.classList.remove("bi-sun");
            icon.classList.add("bi-moon");
        }
    }
}

// --- Sidebar Toggle ---

function initSidebar() {
    const sidebar = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle");
    const closeBtn = document.getElementById("sidebar-close");
    
    if (!sidebar || !toggleBtn) return;

    toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("show");
    });
    
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            sidebar.classList.remove("show");
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener("click", (e) => {
        if (window.innerWidth < 992) {
            if (sidebar.classList.contains("show") && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove("show");
            }
        }
    });
}

// --- Bootstrap Components Initialization ---

function initBootstrapComponents() {
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// --- Notifications Logic ---
async function initNotifications() {
    const notifDropdown = document.getElementById('notifDropdown');
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    
    if (!notifDropdown) return;
    
    // Fetch initial count and list
    fetchNotifications();
    
    // Refresh on open
    notifDropdown.addEventListener('show.bs.dropdown', () => {
        fetchNotifications(true); // true = render list
    });
    
    // Mark all read
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            try {
                const token = localStorage.getItem('access_token') || localStorage.getItem('admin_access_token');
                if (!token) return;
                
                await (window.api ? window.api.patch('/notifications/read-all') : fetch('/api/notifications/read-all', {
                    method: 'PATCH',
                    headers: { 'Authorization': `Bearer ${token}` }
                }));
                fetchNotifications(true);
            } catch(e) { console.error(e); }
        });
    }
}

async function fetchNotifications(renderList = false) {
    const badge = document.getElementById('notifBadge');
    const listEl = document.getElementById('notifList');
    if (!badge) return;
    
    try {
        const token = localStorage.getItem('access_token') || localStorage.getItem('admin_access_token');
        if (!token) return;
        
        const endpoint = '/api/notifications';
        
        const res = await (window.api ? window.api.get(endpoint.replace('/api', '')) : fetch(endpoint, {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => r.json()));
        
        const data = window.api ? res.data : res;
        if (data.status === 'success' && data.data) {
            const notifications = data.data.notifications || [];
            const unreadCount = data.data.unread_count || 0;
            
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
            
            if (renderList && listEl) {
                if (notifications.length === 0) {
                    listEl.innerHTML = '<div class="p-3 text-center text-muted small">No notifications</div>';
                    return;
                }
                
                let html = '';
                notifications.forEach(n => {
                    const bgClass = n.is_read ? 'bg-white' : 'bg-light';
                    let icon = 'bi-info-circle text-primary';
                    if (n.type === 'approval') icon = 'bi-check-circle-fill text-success';
                    if (n.type === 'rejection') icon = 'bi-x-circle-fill text-danger';
                    
                    html += `
                        <div class="d-flex align-items-start p-3 border-bottom ${bgClass} position-relative notif-item" data-id="${n.id}">
                            <i class="bi ${icon} fs-5 me-3"></i>
                            <div>
                                <p class="mb-1 small text-dark">${n.message}</p>
                                <span class="text-muted" style="font-size: 0.7rem;">${new Date(n.created_at).toLocaleString()}</span>
                            </div>
                        </div>
                    `;
                });
                listEl.innerHTML = html;
            }
        }
    } catch(e) { console.error("Error fetching notifications", e); }
}

// --- Global Toast Notification Manager ---

/**
 * Show a toast notification.
 * @param {string} title - The title of the toast.
 * @param {string} message - The body message.
 * @param {string} type - 'success', 'danger', 'warning', 'info'
 */
window.showToast = function(title, message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const id = 'toast-' + Math.random().toString(36).substr(2, 9);
    
    // Map types to Bootstrap contextual classes/icons
    let iconClass = 'bi-info-circle text-info';
    if (type === 'success') iconClass = 'bi-check-circle text-success';
    if (type === 'danger') iconClass = 'bi-exclamation-triangle text-danger';
    if (type === 'warning') iconClass = 'bi-exclamation-circle text-warning';

    const toastHTML = `
        <div id="${id}" class="toast align-items-center" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi ${iconClass} me-2 fs-5"></i>
                <strong class="me-auto">${title}</strong>
                <small class="text-muted">Just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(id);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Clean up DOM after hide
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
};
