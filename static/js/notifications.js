/**
 * Notifications Logic
 * Handles fetching, rendering, marking as read, deleting, and polling.
 */

document.addEventListener('DOMContentLoaded', () => {
    const notificationsList = document.getElementById('notificationsList');
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    const unreadBadge = document.getElementById('navbarUnreadBadge'); // Assuming this exists in navbar
    const filterSelect = document.getElementById('notificationFilter');
    
    let currentFilter = 'all'; // all, unread

    // ==========================================
    // Fetch & Render
    // ==========================================
    async function fetchNotifications() {
        if (!notificationsList) return;
        
        try {
            let url = '/api/notifications/';
            if (currentFilter === 'unread') {
                url += '?is_read=false';
            }

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    // Handled globally if using api.js, but for raw fetch:
                    console.warn('Unauthorized to fetch notifications');
                    return;
                }
                throw new Error('API Error');
            }

            const data = await response.json();
            if (data.status === 'success') {
                // Paginated response structure: data.data.items
                const items = data.data?.items || [];
                renderNotifications(items);
                // unread_count is merged into data.data
                updateUnreadBadge(data.data?.unread_count || 0);
            }
        } catch (error) {
            console.error('Failed to fetch notifications:', error);
            notificationsList.innerHTML = `
                <div class="empty-state text-danger">
                    <i class="bi bi-exclamation-triangle empty-state-icon"></i>
                    <h5 class="fw-bold">Error Loading Notifications</h5>
                    <p class="text-muted">Could not connect to the server.</p>
                </div>
            `;
        }
    }

    function renderNotifications(notifications) {
        notificationsList.innerHTML = '';

        if (notifications.length === 0) {
            notificationsList.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-bell-slash empty-state-icon"></i>
                    <h5 class="fw-bold">No notifications</h5>
                    <p class="text-muted">You're all caught up!</p>
                </div>
            `;
            return;
        }

        notifications.forEach((n, index) => {
            const isUnread = !n.is_read;
            
            // Icon mapping
            let iconClass = 'bi-info-circle';
            let colorClass = 'type-general';
            
            if (n.type === 'approval') { iconClass = 'bi-check-circle'; colorClass = 'type-approval'; }
            else if (n.type === 'rejection') { iconClass = 'bi-x-circle'; colorClass = 'type-rejection'; }
            else if (n.type === 'event_reminder') { iconClass = 'bi-calendar-event'; colorClass = 'type-event_reminder'; }
            else if (n.type === 'announcement') { iconClass = 'bi-megaphone'; colorClass = 'type-announcement'; }
            else if (n.type === 'certificate') { iconClass = 'bi-award-fill'; colorClass = 'type-approval text-warning'; }
            else if (n.notification_type) { // fallback based on DB ENUMs
                if (n.notification_type === 'request_update') { iconClass = 'bi-check2-square'; colorClass = 'type-approval'; }
                if (n.notification_type === 'event_reminder') { iconClass = 'bi-calendar-event'; colorClass = 'type-event_reminder'; }
                if (n.notification_type === 'system') { iconClass = 'bi-info-circle'; colorClass = 'type-general'; }
            }
            
            // Time formatting
            function formatTimeAgo(dateString) {
                if (!dateString) return 'Just now';
                const date = new Date(dateString);
                const seconds = Math.floor((new Date() - date) / 1000);
                
                if (seconds < 60) return 'Just now';
                const minutes = Math.floor(seconds / 60);
                if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
                const hours = Math.floor(minutes / 60);
                if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
                const days = Math.floor(hours / 24);
                if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`;
                
                return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
            }
            
            const dateStr = formatTimeAgo(n.created_at);

            const item = document.createElement('div');
            item.className = `notification-item animate-fade-in-up stagger-${(index % 4) + 1} ${isUnread ? 'unread' : ''}`;
            item.innerHTML = `
                <div class="notification-icon ${colorClass}">
                    <i class="bi ${iconClass}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${n.title}</div>
                    <div class="notification-message">${n.message}</div>
                    ${n.type === 'certificate' && n.related ? `<div class="mt-2"><a href="/certificate/${n.related.id}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="bi bi-download me-1"></i> Download Certificate</a></div>` : ''}
                    <div class="notification-time mt-2"><i class="bi bi-clock"></i> ${dateStr}</div>
                </div>
                <div class="notification-actions">
                    ${isUnread ? `<button class="btn btn-outline-primary btn-icon btn-sm mark-read-btn" data-id="${n._id || n.id}" title="Mark as read"><i class="bi bi-check2"></i></button>` : ''}
                    <button class="btn btn-outline-danger btn-icon btn-sm delete-btn" data-id="${n._id || n.id}" title="Delete"><i class="bi bi-trash"></i></button>
                </div>
            `;
            notificationsList.appendChild(item);
        });

        attachActionListeners();
    }

    // ==========================================
    // Actions & Listeners
    // ==========================================
    function attachActionListeners() {
        document.querySelectorAll('.mark-read-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                // Optmistic UI Update
                const item = e.currentTarget.closest('.notification-item');
                item.classList.remove('unread');
                e.currentTarget.remove();
                
                try {
                    await fetch(`/api/notifications/${id}/read`, { 
                        method: 'PATCH',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
                    });
                } catch(e) {} // Ignore error for mock
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                // Optmistic UI Update
                const item = e.currentTarget.closest('.notification-item');
                item.style.transform = 'translateX(100%)';
                item.style.opacity = '0';
                setTimeout(() => item.remove(), 300);
                
                try {
                    await fetch(`/api/notifications/${id}`, { 
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
                    });
                } catch(e) {} // Ignore error for mock
            });
        });
    }

    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async () => {
            // Optmistic UI Update
            document.querySelectorAll('.notification-item').forEach(item => item.classList.remove('unread'));
            document.querySelectorAll('.mark-read-btn').forEach(btn => btn.remove());
            updateUnreadBadge(0);
            
            try {
                await fetch(`/api/notifications/read-all`, { 
                    method: 'PATCH',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
                });
            } catch(e) {}
        });
    }

    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => {
            currentFilter = e.target.value;
            renderSkeletons();
            setTimeout(fetchNotifications, 300); // Small delay for effect
        });
    }

    function renderSkeletons() {
        if (!notificationsList) return;
        notificationsList.innerHTML = '';
        for (let i = 0; i < 4; i++) {
            notificationsList.innerHTML += `<div class="skeleton-item skeleton"></div>`;
        }
    }

    function updateUnreadBadge(count) {
        if (unreadBadge) {
            unreadBadge.textContent = count;
            unreadBadge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

    // ==========================================
    // Real-time Polling Architecture
    // ==========================================
    // Poll the API every 30 seconds for new notifications
    function startPolling() {
        setInterval(() => {
            // Only poll if tab is visible to save resources
            if (document.visibilityState === 'visible') {
                fetchNotifications();
            }
        }, 30000);
    }

    // Initialize
    if (notificationsList) {
        renderSkeletons();
        setTimeout(fetchNotifications, 500); // Simulate initial load delay
        startPolling();
    }
});
