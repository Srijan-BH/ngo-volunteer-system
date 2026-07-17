/**
 * My Events JavaScript
 * Fetches and displays the user's approved and attended events.
 */

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('eventsContainer');
    const tabs = document.querySelectorAll('#eventsTabs button');
    const paginationInfo = document.getElementById('paginationInfo');
    const paginationControls = document.getElementById('paginationControls');
    
    let currentStatus = 'approved'; // default tab
    let currentPage = 1;
    const pageSize = 9; // Grid of 3x3

    // Initialize tabs
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            currentStatus = e.target.getAttribute('data-status');
            currentPage = 1; // reset on tab change
            fetchEvents();
        });
    });

    async function fetchEvents() {
        renderSkeletons();

        // We use the requests endpoint filtered by status (approved = upcoming, attended = past)
        const url = `/api/requests/my-requests?status=${currentStatus}&page=${currentPage}&page_size=${pageSize}`;

        try {
            const res = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                }
            });

            if (!res.ok) throw new Error('Failed to fetch');

            const data = await res.json();
            if (data.status === 'success') {
                renderEvents(data.data || []);
                renderPagination(data.meta);
            }
        } catch (error) {
            console.error('Error fetching events:', error);
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-exclamation-triangle text-danger" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">Failed to load events</h5>
                    <p class="text-muted">Please try again later.</p>
                </div>
            `;
        }
    }

    function renderSkeletons() {
        container.innerHTML = '';
        for (let i = 0; i < 3; i++) {
            container.innerHTML += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card bg-tertiary border-0 shadow-sm p-4 h-100 skeleton">
                        <div class="skeleton-text skeleton-title mb-2"></div>
                        <div class="skeleton-text"></div>
                        <div class="skeleton-text w-50"></div>
                    </div>
                </div>
            `;
        }
    }

    function renderEvents(requests) {
        container.innerHTML = '';

        if (requests.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5 animate-fade-in-up">
                    <i class="bi bi-calendar-x text-muted" style="font-size: 4rem;"></i>
                    <h4 class="mt-3 fw-bold text-muted">No Events Found</h4>
                    <p class="text-muted">You have no ${currentStatus === 'approved' ? 'upcoming approved' : 'past attended'} events.</p>
                    ${currentStatus === 'approved' ? '<a href="/dashboard" class="btn btn-primary mt-2 rounded-pill">Browse Events</a>' : ''}
                </div>
            `;
            return;
        }

        // Store requests globally so we can access them when "View Details" is clicked
        window.currentRequests = requests;

        requests.forEach((req, idx) => {
            const event = req.event || {};
            const eventDate = event.date ? new Date(event.date).toLocaleDateString() : 'N/A';
            const imageUrl = event.image_url || '/static/images/event-placeholder.jpg';
            
            // Extract the location string from the location object
            let locationStr = 'TBA';
            if (event.location) {
                locationStr = event.location.venue || event.location.city || event.location.address || 'TBA';
            }

            let extraInfo = '';
            if (currentStatus === 'attended') {
                extraInfo = `<div class="mt-2 text-success fw-bold"><i class="bi bi-award me-1"></i> ${req.hours_logged || 0} Hours Credited</div>`;
            } else {
                extraInfo = `<div class="mt-2 text-primary fw-medium"><i class="bi bi-geo-alt me-1"></i> ${locationStr}</div>`;
            }

            container.innerHTML += `
                <div class="col-md-6 col-lg-4 mb-4 animate-fade-in-up stagger-${(idx % 6) + 1}">
                    <div class="card bg-tertiary border-0 shadow-sm h-100 overflow-hidden event-card">
                        <div class="event-image-wrapper" style="height: 160px; overflow: hidden;">
                            <img src="${imageUrl}" class="w-100 h-100" style="object-fit: cover;" alt="${event.title}">
                        </div>
                        <div class="card-body d-flex flex-column">
                            <h5 class="fw-bold mb-2">${event.title || 'Unknown Event'}</h5>
                            <div class="text-muted small mb-3 flex-grow-1">
                                <p class="mb-1"><i class="bi bi-calendar-event me-1"></i> ${eventDate}</p>
                                ${extraInfo}
                            </div>
                            <div class="d-flex justify-content-between align-items-center border-top border-secondary pt-3 mt-auto">
                                <span class="badge ${currentStatus === 'approved' ? 'bg-success' : 'bg-info text-dark'} px-3 py-2 rounded-pill">
                                    <i class="bi bi-check2-circle me-1"></i> ${currentStatus === 'approved' ? 'Approved' : 'Attended'}
                                </span>
                                <div>
                                    <a href="/chat?event_id=${event._id}&title=${encodeURIComponent(event.title || 'Event')}" class="btn btn-sm btn-outline-success rounded-pill me-1" title="Event Chat">
                                        <i class="bi bi-chat-dots"></i> Chat
                                    </a>
                                    <button class="btn btn-sm btn-outline-primary rounded-pill view-details-btn" data-index="${idx}">
                                        Details
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        // Attach event listeners for View Details buttons
        document.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = e.currentTarget.getAttribute('data-index');
                openEventDetailsModal(window.currentRequests[idx].event);
            });
        });
    }

    function openEventDetailsModal(event) {
        if (!event) return;
        
        document.getElementById('modalEventTitle').textContent = event.title || 'Unknown Event';
        document.getElementById('modalEventImage').src = event.banner_image || 'https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=800&q=80';
        document.getElementById('modalEventCategory').textContent = event.category_name || 'General';
        
        const eventDate = event.date ? new Date(event.date).toLocaleDateString() : 'N/A';
        const eventTime = event.start_time || 'N/A';
        document.getElementById('modalEventDate').innerHTML = `<i class="bi bi-calendar3 me-1"></i> ${eventDate}`;
        document.getElementById('modalEventTime').innerHTML = `<i class="bi bi-clock me-1"></i> ${eventTime}`;
        
        document.getElementById('modalEventDesc').textContent = event.description || 'No description provided.';
        
        let locationStr = 'TBA';
        if (event.location) {
            locationStr = [event.location.venue, event.location.address, event.location.city, event.location.state]
                .filter(Boolean).join(', ') || 'TBA';
        }
        document.getElementById('modalEventLocation').textContent = locationStr;
        
        const maxVolunteers = event.max_participants || 0;
        const currentVolunteers = event.current_participants || 0;
        const capacityStr = maxVolunteers > 0 
            ? `${currentVolunteers} / ${maxVolunteers} Volunteers`
            : `${currentVolunteers} Volunteers (No Limit)`;
        document.getElementById('modalEventCapacity').textContent = capacityStr;
        
        const modalEl = document.getElementById('eventDetailsModal');
        // Move modal to body to prevent stacking context issues (e.g., getting stuck behind backdrop)
        if (modalEl.parentNode !== document.body) {
            document.body.appendChild(modalEl);
        }
        
        const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        modal.show();
    }

    function renderPagination(meta) {
        const start = (meta.page - 1) * meta.page_size + 1;
        const end = Math.min(meta.page * meta.page_size, meta.total);
        
        if (meta.total === 0) {
            paginationInfo.textContent = 'Showing 0-0 of 0 events';
            paginationControls.innerHTML = '';
            return;
        }

        paginationInfo.textContent = `Showing ${start}-${end} of ${meta.total} events`;

        let pgHtml = '';
        if (meta.page > 1) {
            pgHtml += `<li class="page-item"><a class="page-link page-btn" href="#" data-page="${meta.page - 1}">Previous</a></li>`;
        } else {
            pgHtml += `<li class="page-item disabled"><span class="page-link">Previous</span></li>`;
        }

        for (let i = 1; i <= meta.total_pages; i++) {
            if (i === meta.page) {
                pgHtml += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
            } else {
                pgHtml += `<li class="page-item"><a class="page-link page-btn" href="#" data-page="${i}">${i}</a></li>`;
            }
        }

        if (meta.page < meta.total_pages) {
            pgHtml += `<li class="page-item"><a class="page-link page-btn" href="#" data-page="${meta.page + 1}">Next</a></li>`;
        } else {
            pgHtml += `<li class="page-item disabled"><span class="page-link">Next</span></li>`;
        }

        paginationControls.innerHTML = pgHtml;

        document.querySelectorAll('.page-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                currentPage = parseInt(e.target.getAttribute('data-page'));
                fetchEvents();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }

    // Initial load
    fetchEvents();
});
