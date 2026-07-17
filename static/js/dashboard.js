/**
 * Volunteer Dashboard JavaScript
 * Fetches real statistics, renders dynamic lists, and mounts Chart.js graphs.
 */

document.addEventListener('DOMContentLoaded', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
    const textColor = isDark ? '#cbd5e1' : '#64748b';

    async function loadDashboard() {
        try {
            const response = await fetch('/api/dashboard/volunteer', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
            });
            
            if (!response.ok) throw new Error("Failed to load dashboard data");
            const resData = await response.json();
            
            if (resData.status === 'success') {
                const data = resData.data;
                populateWelcomeBanner(data.user_info, data.stats);
                populateStatsCards(data.stats);
                populateProfileCard(data.user_info, data.stats);
                populateUpcomingList(data.upcoming_events);
                populateNotifications(data.notifications, data.unread_notifications_count);
                populatePendingRequests(data.pending_requests);
                populateHistoryList(data.history);
                
                renderHoursChart(data.hours_trend);
                renderCategoryChart(data.categories);
            }
        } catch (error) {
            console.error(error);
            // Fallback error UI could be injected here
        }
    }

    // ==========================================
    // DOM Populators
    // ==========================================

    function populateWelcomeBanner(userInfo, stats) {
        document.getElementById('dashWelcomeSkeleton').style.display = 'none';
        
        const hour = new Date().getHours();
        let timeOfDay = 'morning';
        if (hour >= 12 && hour < 17) timeOfDay = 'afternoon';
        else if (hour >= 17) timeOfDay = 'evening';
        
        document.getElementById('timeOfDay').textContent = timeOfDay;
        document.getElementById('dashUserFirstName').textContent = userInfo.first_name || 'Volunteer';
        
        const banner = document.getElementById('dashWelcomeBanner');
        banner.style.display = 'block';
        
        const subtitle = document.getElementById('dashWelcomeSubtitle');
        subtitle.innerHTML = `You've volunteered <strong>${stats.hours_logged} hours</strong> so far. Keep making a difference!`;
    }

    function populateStatsCards(stats) {
        document.getElementById('statJoinedEvents').textContent = stats.joined_events;
        document.getElementById('statHoursLogged').textContent = stats.hours_logged;
        document.getElementById('statPendingRequests').textContent = stats.pending_requests;
        document.getElementById('statCertificates').textContent = stats.certificates;
    }

    function populateProfileCard(userInfo, stats) {
        document.getElementById('profileFullName').textContent = `${userInfo.first_name} ${userInfo.last_name}`;
        
        if (userInfo.created_at) {
            const date = new Date(userInfo.created_at);
            const month = date.toLocaleString('default', { month: 'short' });
            document.getElementById('profileJoinDate').textContent = `Volunteer since ${month} ${date.getFullYear()}`;
        }
        
        document.getElementById('profileCompletionText').textContent = `${userInfo.completion_percentage}%`;
        document.getElementById('profileCompletionBar').style.width = `${userInfo.completion_percentage}%`;
        
        document.getElementById('profileStatEvents').textContent = stats.joined_events;
        document.getElementById('profileStatHours').textContent = `${stats.hours_logged}h`;
        document.getElementById('profileStatBadges').textContent = stats.certificates;
    }

    function populateUpcomingList(events) {
        const container = document.getElementById('dashUpcomingList');
        if (!events || events.length === 0) {
            container.innerHTML = `
                <div class="p-4 text-center text-muted">
                    <i class="bi bi-calendar-x display-6 mb-2 text-secondary"></i>
                    <p class="mb-0">No upcoming events right now.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        events.forEach(ev => {
            const date = new Date(ev.start_date);
            
            let timeStr = '12:00 am';
            if (ev.start_time) {
                const [h, m] = ev.start_time.split(':');
                let hours = parseInt(h, 10);
                const ampm = hours >= 12 ? 'pm' : 'am';
                hours = hours % 12;
                hours = hours ? hours : 12;
                timeStr = `${hours}:${m} ${ampm}`;
            } else {
                timeStr = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            }

            container.innerHTML += `
                <div class="event-list-item">
                    <div class="event-date-block">
                        <span class="day">${date.getDate()}</span>
                        <span class="month">${date.toLocaleString('default', {month:'short'})}</span>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="fw-bold mb-1">${ev.title}</h6>
                        <div class="d-flex flex-wrap gap-2 small text-muted">
                            <span><i class="bi bi-geo-alt me-1 text-primary"></i>${ev.location}</span>
                            <span><i class="bi bi-clock me-1"></i>${timeStr}</span>
                        </div>
                    </div>
                    <span class="badge bg-primary bg-opacity-10 text-primary rounded-pill">Upcoming</span>
                </div>
            `;
        });
    }

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
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function populateNotifications(notifications, unreadCount) {
        const container = document.getElementById('dashNotifList');
        const badge = document.getElementById('dashNotifBadge');
        
        if (unreadCount > 0) {
            badge.textContent = `${unreadCount} new`;
            badge.style.display = 'inline-block';
        }
        
        if (!notifications || notifications.length === 0) {
            container.innerHTML = `
                <div class="p-4 text-center text-muted">
                    <p class="mb-0">You're all caught up!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        notifications.forEach(n => {
            const isUnread = !n.is_read;
            let iconClass = 'bi-info-circle-fill';
            let colorClass = 'text-secondary bg-secondary';
            
            if (n.type === 'approval') { iconClass = 'bi-check-circle-fill'; colorClass = 'text-success bg-success'; }
            else if (n.type === 'rejection') { iconClass = 'bi-x-circle-fill'; colorClass = 'text-danger bg-danger'; }
            else if (n.type === 'event_reminder') { iconClass = 'bi-clock-fill'; colorClass = 'text-warning bg-warning'; }
            else if (n.type === 'announcement') { iconClass = 'bi-megaphone-fill'; colorClass = 'text-primary bg-primary'; }
            
            container.innerHTML += `
                <a href="/notifications" class="notif-item text-decoration-none text-dark ${isUnread ? 'unread' : ''}">
                    <div class="notif-icon ${colorClass} bg-opacity-10"><i class="bi ${iconClass}"></i></div>
                    <div class="flex-grow-1">
                        <p class="mb-0 small fw-bold">${n.title}</p>
                        <p class="mb-0 text-muted" style="font-size: 0.78rem;">${n.message}</p>
                        <span class="text-muted" style="font-size: 0.7rem;">${formatTimeAgo(n.created_at)}</span>
                    </div>
                </a>
            `;
        });
    }

    function populatePendingRequests(requests) {
        const container = document.getElementById('dashPendingList');
        if (!requests || requests.length === 0) {
            container.innerHTML = `
                <div class="p-4 text-center text-muted">
                    <p class="mb-0">No pending requests.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = '';
        requests.forEach(req => {
            container.innerHTML += `
                <div class="event-list-item">
                    <div class="flex-grow-1">
                        <h6 class="fw-bold mb-0 small">${req.title}</h6>
                        <span class="text-muted" style="font-size: 0.75rem;">Applied ${formatTimeAgo(req.applied_date)}</span>
                    </div>
                    <span class="badge bg-warning bg-opacity-10 text-warning rounded-pill small">Pending</span>
                </div>
            `;
        });
    }

    function populateHistoryList(history) {
        const tbody = document.getElementById('dashHistoryList');
        if (!history || history.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center py-4 text-muted">
                        No event history found. Join an event to get started!
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        history.forEach(item => {
            const date = new Date(item.start_date);
            let badgeClass = item.status === 'Attended' ? 'bg-success text-success' : 'bg-primary text-primary';
            
            let feedbackHtml = '';
            if (item.status === 'Attended') {
                if (item.rating) {
                    feedbackHtml = `<span class="badge bg-warning bg-opacity-10 text-warning rounded-pill"><i class="bi bi-star-fill me-1"></i>${item.rating}/5</span>`;
                } else {
                    const safeTitle = item.title ? item.title.replace(/"/g, '&quot;') : 'Event';
                    feedbackHtml = `<button class="btn btn-sm btn-outline-primary rounded-pill py-0 px-2 btn-leave-feedback" data-request-id="${item.request_id}" data-event-title="${safeTitle}">Rate</button>`;
                }
            }

            tbody.innerHTML += `
                <tr>
                    <td class="ps-4">
                        <div class="d-flex align-items-center gap-3">
                            <div class="bg-primary bg-opacity-10 text-primary rounded p-2"><i class="bi bi-calendar2-check"></i></div>
                            <div>
                                <h6 class="mb-0 fw-bold small">${item.title}</h6>
                                <span class="text-muted" style="font-size: 0.75rem;">${item.location}</span>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge bg-secondary bg-opacity-10 text-secondary rounded-pill">${item.category || 'General'}</span></td>
                    <td class="small">${date.toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'})}</td>
                    <td class="fw-bold small">${item.hours_logged}h</td>
                    <td>
                        <div class="d-flex flex-column gap-1 align-items-start">
                            <span class="badge ${badgeClass} bg-opacity-10 rounded-pill">${item.status}</span>
                            ${feedbackHtml}
                        </div>
                    </td>
                </tr>
            `;
        });
        
        // Attach event listeners for feedback buttons
        document.querySelectorAll('.btn-leave-feedback').forEach(btn => {
            btn.addEventListener('click', function() {
                openFeedbackModal(this.dataset.requestId, this.dataset.eventTitle);
            });
        });
    }

    // ==========================================
    // Feedback Modal Logic
    // ==========================================
    let currentFeedbackRequestId = null;
    let currentRating = 0;

    function openFeedbackModal(requestId, eventTitle) {
        currentFeedbackRequestId = requestId;
        currentRating = 0;
        document.getElementById('feedbackEventTitle').textContent = eventTitle;
        document.getElementById('feedbackComment').value = '';
        updateStars(0);
        
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('feedbackModal'));
        modal.show();
    }

    // Handle star clicks
    document.querySelectorAll('.rating-stars i').forEach(star => {
        star.addEventListener('click', function() {
            currentRating = parseInt(this.dataset.rating);
            updateStars(currentRating);
        });
        // Hover effects
        star.addEventListener('mouseover', function() {
            updateStars(parseInt(this.dataset.rating), true);
        });
    });
    
    document.querySelector('.rating-stars').addEventListener('mouseout', function() {
        updateStars(currentRating); // Reset to selected on mouse out
    });

    function updateStars(rating, isHover = false) {
        document.querySelectorAll('.rating-stars i').forEach(s => {
            const starValue = parseInt(s.dataset.rating);
            if (starValue <= rating) {
                s.className = isHover ? 'bi bi-star-fill text-warning opacity-75' : 'bi bi-star-fill text-warning';
            } else {
                s.className = 'bi bi-star text-warning';
            }
        });
    }

    // Handle submit
    const submitBtn = document.getElementById('submitFeedbackBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', async function() {
            if (currentRating === 0) {
                alert('Please select a star rating.');
                return;
            }
            
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Submitting...';
            
            const comment = document.getElementById('feedbackComment').value;
            
            try {
                const response = await fetch(`/api/requests/${currentFeedbackRequestId}/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` },
                    body: JSON.stringify({ rating: currentRating, feedback: comment })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    const modalEl = document.getElementById('feedbackModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                    
                    // Reload dashboard data to show the updated history UI
                    loadDashboard();
                } else {
                    alert(data.message || 'Failed to submit feedback.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred.');
            } finally {
                this.disabled = false;
                this.innerHTML = 'Submit Feedback';
            }
        });
    }

    // ==========================================
    // Chart Renderers
    // ==========================================

    function renderHoursChart(trendData) {
        const hoursCtx = document.getElementById('hoursChart');
        if (!hoursCtx) return;
        
        // Use real data, or fake data if array is empty
        let labels = [];
        let data = [];
        
        if (trendData && trendData.length > 0) {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            trendData.forEach(d => {
                labels.push(`${months[d.month - 1]} ${d.year}`);
                data.push(d.hours);
            });
        } else {
            labels = ['No Activity'];
            data = [0];
        }

        new Chart(hoursCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Hours',
                    data: data,
                    backgroundColor: [
                        'rgba(79, 70, 229, 0.7)',
                        'rgba(99, 102, 241, 0.7)',
                        'rgba(129, 140, 248, 0.7)',
                        'rgba(79, 70, 229, 0.7)',
                        'rgba(99, 102, 241, 0.7)',
                        'rgba(139, 92, 246, 0.7)',
                    ],
                    borderRadius: 8,
                    borderSkipped: false,
                    barPercentage: 0.5,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDark ? '#1e293b' : '#fff',
                        titleColor: isDark ? '#f8fafc' : '#0f172a',
                        bodyColor: isDark ? '#cbd5e1' : '#475569',
                        borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12,
                        callbacks: {
                            label: ctx => ` ${ctx.parsed.y} hours`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor, drawBorder: false },
                        ticks: { color: textColor, font: { size: 12 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: textColor, font: { size: 12, weight: 500 } }
                    }
                }
            }
        });
    }

    function renderCategoryChart(catData) {
        const catCtx = document.getElementById('categoryChart');
        if (!catCtx) return;
        
        let labels = [];
        let data = [];
        
        if (catData && catData.length > 0) {
            catData.forEach(c => {
                labels.push(c.category || 'General');
                data.push(c.count);
            });
        } else {
            labels = ['No Data'];
            data = [1];
        }

        new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#10b981', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4'
                    ],
                    borderWidth: 0,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '68%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 16,
                            color: textColor,
                            font: { size: 12, weight: 500 }
                        }
                    },
                    tooltip: {
                        backgroundColor: isDark ? '#1e293b' : '#fff',
                        titleColor: isDark ? '#f8fafc' : '#0f172a',
                        bodyColor: isDark ? '#cbd5e1' : '#475569',
                        borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12
                    }
                }
            }
        });
    }

    // Initialize Dashboard
    loadDashboard();
});
