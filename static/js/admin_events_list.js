/**
 * Admin Events List Logic
 * Handles fetching events, filtering, pagination, and status changes.
 */

document.addEventListener('DOMContentLoaded', () => {
    const eventList = document.getElementById('adminEventList');
    const searchInput = document.getElementById('eventSearch');
    const statusFilter = document.getElementById('statusFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    
    let currentPage = 1;
    let currentData = [];

    // ==========================================
    // Fetch & Render
    // ==========================================
    async function fetchEvents(page = 1) {
        currentPage = page;
        if (!eventList) return;
        
        eventList.innerHTML = `<div class="col-12 text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        
        try {
            // Build query params
            const params = new URLSearchParams({ page: page, page_size: 10 });
            if (statusFilter.value) params.append('status', statusFilter.value);
            if (categoryFilter.value) params.append('category', categoryFilter.value);
            
            // If searching, we use the search endpoint instead
            let url = `/api/events?${params.toString()}`;
            if (searchInput.value.trim()) {
                params.append('q', searchInput.value.trim());
                url = `/api/events/search?${params.toString()}`;
            }

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('jwt_token') || ''}` }
            });
            
            if (!response.ok) throw new Error('API Error');

            const data = await response.json();
            if (data.status === 'success') {
                // Search endpoint returns {events, count}, standard returns paginated format
                const events = data.data.events || data.data; 
                currentData = events;
                renderEvents(events);
                // Simple mock pagination for demo if search doesn't return meta
                if (data.meta) renderPagination(data.meta);
            }
        } catch (error) {
            console.warn('Failed to fetch from API, falling back to mock data.', error);
            renderMockEvents();
        }
    }

    function renderEvents(events) {
        eventList.innerHTML = '';

        if (events.length === 0) {
            eventList.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-calendar-x display-1 text-muted mb-3 d-block"></i>
                    <h5 class="fw-bold">No events found</h5>
                    <p class="text-muted">Try adjusting your filters or search query.</p>
                </div>
            `;
            return;
        }

        events.forEach((event, index) => {
            const startDate = new Date(event.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            const statusColors = {
                'published': 'success',
                'draft': 'warning text-dark',
                'completed': 'info text-dark',
                'cancelled': 'danger'
            };
            const sColor = statusColors[event.status] || 'secondary';

            const card = document.createElement('div');
            card.className = 'col-12';
            card.innerHTML = `
                <div class="event-list-card animate-fade-in-up stagger-${(index % 4) + 1}">
                    <div class="event-banner">
                        <img src="${event.image_url || 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=400&q=80'}" alt="Banner">
                        <div class="event-status-badge text-bg-${sColor}">${event.status}</div>
                    </div>
                    
                    <div class="event-details">
                        <div>
                            <h3 class="event-title">${event.title}</h3>
                            <div class="event-meta">
                                <span><i class="bi bi-calendar"></i> ${startDate}</span>
                                <span><i class="bi bi-geo-alt"></i> ${event.is_virtual ? 'Virtual' : event.location || 'TBA'}</span>
                                <span><i class="bi bi-tag"></i> <span class="text-capitalize">${event.category || 'Other'}</span></span>
                            </div>
                        </div>
                        
                        <div class="event-stats">
                            <div class="stat-item">
                                <span class="val">${event.current_volunteers || 0}/${event.max_volunteers || '∞'}</span>
                                <span class="lbl">Volunteers</span>
                            </div>
                            <div class="stat-item">
                                <span class="val">${event.views || 0}</span>
                                <span class="lbl">Views</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="event-actions">
                        <a href="#" class="btn btn-sm btn-outline-primary btn-icon-text">
                            <i class="bi bi-pencil"></i> Edit
                        </a>
                        <div class="dropdown w-100 mt-2">
                            <button class="btn btn-sm btn-outline-secondary w-100 dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                Options
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow">
                                <li><a class="dropdown-item status-change" href="#" data-id="${event.id || event._id}" data-status="published">Publish</a></li>
                                <li><a class="dropdown-item status-change" href="#" data-id="${event.id || event._id}" data-status="completed">Mark Completed</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger delete-event" href="#" data-id="${event.id || event._id}">Delete Event</a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
            eventList.appendChild(card);
        });

        attachActionListeners();
    }

    function renderMockEvents() {
        const mockData = [
            { _id: '1', title: 'Annual Beach Cleanup', status: 'published', start_date: new Date().toISOString(), location: 'Juhu Beach', category: 'environment', max_volunteers: 50, current_volunteers: 25, is_virtual: false },
            { _id: '2', title: 'Online Tutoring Orientation', status: 'draft', start_date: new Date(Date.now() + 86400000).toISOString(), location: 'Zoom', category: 'education', max_volunteers: 0, current_volunteers: 0, is_virtual: true },
            { _id: '3', title: 'Food Drive 2026', status: 'completed', start_date: new Date(Date.now() - 86400000 * 5).toISOString(), location: 'City Center', category: 'community', max_volunteers: 100, current_volunteers: 100, is_virtual: false }
        ];
        
        let filtered = mockData;
        if (statusFilter.value) filtered = filtered.filter(e => e.status === statusFilter.value);
        if (categoryFilter.value) filtered = filtered.filter(e => e.category === categoryFilter.value);
        if (searchInput.value) filtered = filtered.filter(e => e.title.toLowerCase().includes(searchInput.value.toLowerCase()));
        
        renderEvents(filtered);
    }

    // ==========================================
    // Actions & Listeners
    // ==========================================
    function attachActionListeners() {
        document.querySelectorAll('.status-change').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const id = e.currentTarget.getAttribute('data-id');
                const status = e.currentTarget.getAttribute('data-status');
                
                try {
                    await fetch(`/api/events/${id}/status`, { 
                        method: 'PATCH',
                        headers: { 
                            'Authorization': `Bearer ${localStorage.getItem('jwt_token') || ''}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ status })
                    });
                    showToast('Success', `Event status changed to ${status}`, 'success');
                    fetchEvents(currentPage);
                } catch(err) {
                    showToast('Success', `(Mock) Event status changed to ${status}`, 'success');
                    fetchEvents(currentPage);
                }
            });
        });

        document.querySelectorAll('.delete-event').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                if(!confirm("Are you sure you want to delete this event? This cannot be undone.")) return;
                
                const id = e.currentTarget.getAttribute('data-id');
                try {
                    await fetch(`/api/events/${id}`, { 
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('jwt_token') || ''}` }
                    });
                    showToast('Success', 'Event deleted successfully', 'success');
                    fetchEvents(currentPage);
                } catch(err) {
                    showToast('Success', '(Mock) Event deleted', 'success');
                    fetchEvents(currentPage);
                }
            });
        });
    }

    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => fetchEvents(1), 500);
        });
    }

    if (statusFilter) statusFilter.addEventListener('change', () => fetchEvents(1));
    if (categoryFilter) categoryFilter.addEventListener('change', () => fetchEvents(1));

    // Global Toast Notification Helper
    function showToast(title, message, type='primary') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        const toastId = 'toast-' + Date.now();
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>`;
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(toastId);
        new bootstrap.Toast(toastEl, { delay: 3000 }).show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    function renderPagination(meta) {
        // Simplified pagination render
        const ul = document.getElementById('eventsPagination');
        if(!ul) return;
        ul.innerHTML = '';
        for(let i=1; i<=meta.total_pages; i++){
            ul.innerHTML += `<li class="page-item ${i === meta.page ? 'active' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); window.fetchEvents(${i})">${i}</a></li>`;
        }
    }
    window.fetchEvents = fetchEvents;

    // Initialize
    if (eventList) {
        fetchEvents(1);
    }
});
