/**
 * Admin Dashboard Controller
 * Fetches dynamic data from the backend and populates the dashboard UI.
 */
document.addEventListener('DOMContentLoaded', () => {
    fetchAdminOverview();
});

async function fetchAdminOverview() {
    try {
        const token = localStorage.getItem('admin_access_token');
        if (!token) {
            window.location.href = '/admin/login';
            return;
        }

        const [overviewRes, trendsRes, categoriesRes] = await Promise.all([
            fetch('/api/dashboard/overview', { headers: { 'Authorization': `Bearer ${token}` } }),
            fetch('/api/dashboard/event-trends', { headers: { 'Authorization': `Bearer ${token}` } }),
            fetch('/api/dashboard/categories', { headers: { 'Authorization': `Bearer ${token}` } })
        ]);

        if (overviewRes.ok) {
            const overviewData = await overviewRes.json();
            populateStats(overviewData.data.overview);
            populateRecentUsers(overviewData.data.recent_users);
            populateLatestActivities(overviewData.data.latest_activities);
        }

        if (trendsRes.ok) {
            const trendsData = await trendsRes.json();
            initRegistrationChart(trendsData.data.trends);
        }

        if (categoriesRes.ok) {
            const catData = await categoriesRes.json();
            initEventsChart(catData.data.categories);
        }

    } catch (error) {
        console.error("Error fetching admin dashboard data:", error);
        window.showToast("Error", "Failed to load dashboard data. Please try again.", "danger");
    }
}

function populateStats(stats) {
    document.getElementById('statTotalVolunteers').textContent = stats.volunteers.total.toLocaleString();
    document.getElementById('statTotalEvents').textContent = stats.events.total.toLocaleString();
    document.getElementById('statPendingRequests').textContent = stats.registrations.pending.toLocaleString();
    document.getElementById('statCompletedEvents').textContent = stats.events.completed.toLocaleString();
}

function populateRecentUsers(users) {
    const tableBody = document.getElementById('recentUsersTable');
    tableBody.innerHTML = '';

    if (!users || users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No recent users found.</td></tr>';
        return;
    }

    users.forEach(u => {
        let statusBadge = '<span class="badge-status text-bg-success">Active</span>';
        if (u.is_active === false) statusBadge = '<span class="badge-status text-bg-danger">Inactive</span>';
        else if (u.status === 'pending') statusBadge = '<span class="badge-status text-bg-warning">Pending Review</span>';

        let roleBadge = '<span class="badge bg-secondary">Volunteer</span>';
        if (u.role === 'admin' || u.role === 'super_admin') roleBadge = '<span class="badge bg-danger">Admin</span>';

        const joinedDate = new Date(u.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });

        const row = `
            <tr>
                <td>
                    <div class="table-user">
                        <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(u.full_name)}&background=random" alt="Avatar" class="table-user-avatar">
                        <div class="table-user-info">
                            <span class="table-user-name">${u.full_name}</span>
                            <span class="table-user-email">${u.email}</span>
                        </div>
                    </div>
                </td>
                <td>${roleBadge}</td>
                <td>${statusBadge}</td>
                <td>${joinedDate}</td>
                <td class="text-end">
                    <a href="/admin/volunteers" class="btn btn-sm btn-outline-primary rounded-circle" title="Manage User"><i class="bi bi-pencil"></i></a>
                </td>
            </tr>
        `;
        tableBody.insertAdjacentHTML('beforeend', row);
    });
}

function populateLatestActivities(activities) {
    const list = document.getElementById('latestActivitiesList');
    list.innerHTML = '';

    if (!activities || activities.length === 0) {
        list.innerHTML = '<li class="activity-item text-muted">No recent activities.</li>';
        return;
    }

    activities.forEach(act => {
        const item = `
            <li class="activity-item">
                <div class="activity-icon"><i class="bi ${act.icon}"></i></div>
                <div class="activity-content">
                    <div class="activity-text">${act.text}</div>
                    <div class="activity-time">${formatTimeAgo(act.time)}</div>
                </div>
            </li>
        `;
        list.insertAdjacentHTML('beforeend', item);
    });
}

let trendChartInstance = null;

function initRegistrationChart(trends, range = '6_months') {
    const ctx = document.getElementById('registrationChart');
    if (!ctx || !trends) return;

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    const labels = [];
    const data = [];
    const now = new Date();
    
    if (range === '30_days') {
        for (let i = 29; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
            labels.push(d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
            const found = trends.find(t => t._id.month === d.getMonth() + 1 && t._id.day === d.getDate() && t._id.year === d.getFullYear());
            data.push(found ? found.count : 0);
        }
    } else if (range === 'this_year') {
        for (let i = 0; i <= now.getMonth(); i++) {
            const d = new Date(now.getFullYear(), i, 1);
            labels.push(d.toLocaleString('default', { month: 'short' }));
            const found = trends.find(t => t._id.month === i + 1 && t._id.year === now.getFullYear());
            data.push(found ? found.count : 0);
        }
    } else {
        // Generate the last 6 months
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            labels.push(d.toLocaleString('default', { month: 'short' }));
            const found = trends.find(t => t._id.month === d.getMonth() + 1 && t._id.year === d.getFullYear());
            data.push(found ? found.count : 0);
        }
    }

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'New Events',
                data: data,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { borderDash: [2, 4], color: '#e5e7eb' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function initEventsChart(categories) {
    const ctx = document.getElementById('eventsChart');
    if (!ctx || !categories) return;

    const labels = categories.map(c => c._id);
    const data = categories.map(c => c.count);
    const colors = ['#10b981', '#f59e0b', '#4f46e5', '#ef4444', '#6b7280'];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.length ? labels : ['Community', 'Environment', 'Education'],
            datasets: [{
                data: data.length ? data : [10, 20, 30],
                backgroundColor: colors.slice(0, data.length || 3),
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } }
            }
        }
    });
}

function formatTimeAgo(dateString) {
    if (!dateString) return "Just now";
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return `${Math.floor(diff / 86400)} days ago`;
}

window.updateTrend = async function(range, title) {
    document.getElementById('trendTitle').textContent = `Event Trend (${title})`;
    document.getElementById('trendDropdownBtn').textContent = title;
    
    try {
        const token = localStorage.getItem('admin_access_token');
        const res = await fetch(`/api/dashboard/event-trends?range=${range}`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
            const data = await res.json();
            initRegistrationChart(data.data.trends, range);
        }
    } catch(e) { console.error("Error updating trend:", e); }
};
