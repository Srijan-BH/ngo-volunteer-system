/**
 * Events Page Logic
 * Handles fetching, filtering, sorting, pagination, and countdown timers.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const gridEl = document.getElementById('eventsGrid');
    const searchInput = document.getElementById('searchEvents');
    const categoryFilter = document.getElementById('categoryFilter');
    const sortFilter = document.getElementById('sortFilter');
    const distanceFilterContainer = document.getElementById('distanceFilterContainer');
    const distanceFilter = document.getElementById('distanceFilter');
    const paginationEl = document.getElementById('pagination');
    const btnListView = document.getElementById('btnListView');
    const btnMapView = document.getElementById('btnMapView');
    const mapContainer = document.getElementById('mapContainer');
    const btnNearMe = document.getElementById('btnNearMe');

    // State
    let allEvents = [];
    let filteredEvents = [];
    let currentPage = 1;
    const itemsPerPage = 6;
    let timerInterval = null;
    let isMapView = false;
    let map = null;
    let markersLayer = null;
    let userLat = null;
    let userLng = null;

    // Initialize
    fetchEvents();

    // Event Listeners
    searchInput.addEventListener('input', debounce(applyFilters, 300));
    categoryFilter.addEventListener('change', applyFilters);
    sortFilter.addEventListener('change', applyFilters);
    distanceFilter.addEventListener('change', fetchEvents);

    btnListView.addEventListener('click', () => switchView('list'));
    btnMapView.addEventListener('click', () => switchView('map'));
    btnNearMe.addEventListener('click', handleNearMe);

    // ==========================================
    // Fetch & Render Logic
    // ==========================================
    async function fetchEvents() {
        renderSkeletons();
        
        try {
            let url = '/api/events?';
            if (userLat !== null && userLng !== null) {
                const radius = distanceFilter.value;
                url += `lat=${userLat}&lng=${userLng}&radius=${radius}&`;
            }
            
            // Using the global `api` axios instance if available, otherwise fallback to fetch
            const res = await (window.api ? window.api.get(url) : fetch(url).then(r => r.json()));
            
            const data = window.api ? res.data : res;
            
            if (data.status === 'success') {
                // Map the backend data to the frontend expected format
                allEvents = data.data.items.map(ev => {
                    // Reconstruct the full ISO string for frontend date formatting
                    const start = new Date(`${ev.date}T${ev.start_time}`);
                    const end = ev.end_time ? new Date(`${ev.date}T${ev.end_time}`) : start;
                    
                    return {
                        id: ev.id, // backend serialize returns 'id' not '_id'
                        title: ev.title,
                        description: ev.description,
                        category: ev.category_name || ev.category || 'Other',
                        location: ev.location?.venue || ev.location?.city || 'Online',
                        dateStr: start.toLocaleDateString(),
                        timeStr: `${start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`,
                        timestamp: start.getTime(),
                        image: ev.banner_image || "https://images.unsplash.com/photo-1593113514676-5925330e70ba?auto=format&fit=crop&q=80&w=800",
                        slotsTotal: ev.max_participants || 0,
                        slotsFilled: ev.current_participants || 0,
                        status: ev.status,
                        geo: ev.location_geo
                    };
                });
            } else {
                allEvents = [];
                if (window.showToast) showToast('Error', data.message || 'Failed to load events.', 'danger');
            }
        } catch (error) {
            console.error("Failed to fetch events", error);
            allEvents = [];
            if (window.showToast) showToast('Network Error', 'Could not fetch events from the server.', 'danger');
        }
        
        applyFilters();
    }

    function applyFilters() {
        const query = searchInput.value.toLowerCase();
        const cat = categoryFilter.value;
        const sort = sortFilter.value;

        // Filter
        filteredEvents = allEvents.filter(ev => {
            const matchesSearch = ev.title.toLowerCase().includes(query) || ev.location.toLowerCase().includes(query);
            const matchesCat = cat === 'All' || ev.category === cat;
            return matchesSearch && matchesCat;
        });

        // Sort
        if (sort === 'upcoming') {
            filteredEvents.sort((a, b) => a.timestamp - b.timestamp);
        } else if (sort === 'slots_avail') {
            filteredEvents.sort((a, b) => (b.slotsTotal - b.slotsFilled) - (a.slotsTotal - a.slotsFilled));
        }

        currentPage = 1;
        if (isMapView) {
            renderMap();
        } else {
            renderGrid();
        }
    }

    function renderGrid() {
        gridEl.innerHTML = '';
        if (timerInterval) clearInterval(timerInterval);

        if (filteredEvents.length === 0) {
            gridEl.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-search text-muted fs-1 mb-3"></i>
                    <h5 class="fw-bold">No events found</h5>
                    <p class="text-muted">Try adjusting your search or filters.</p>
                </div>
            `;
            renderPagination(0, 1);
            return;
        }

        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        const pageItems = filteredEvents.slice(startIndex, endIndex);

        pageItems.forEach((ev, index) => {
            const isFull = ev.slotsFilled >= ev.slotsTotal;
            const progressPct = (ev.slotsFilled / ev.slotsTotal) * 100;
            const isPast = ev.timestamp < new Date().getTime();
            
            // Badge color based on category
            let badgeClass = 'bg-primary';
            if (ev.category === 'Environment') badgeClass = 'bg-success';
            if (ev.category === 'Health') badgeClass = 'bg-danger';
            if (ev.category === 'Education') badgeClass = 'bg-info';
            if (ev.category === 'Social Welfare') badgeClass = 'bg-warning text-dark';

            let btnClass = 'btn-primary';
            let btnText = 'Request to Join';
            let isDisabled = false;
            
            if (isPast) {
                btnClass = 'btn-secondary';
                btnText = 'Registration Closed';
                isDisabled = true;
            } else if (isFull) {
                btnClass = 'btn-secondary';
                btnText = 'Waitlist Full';
                isDisabled = true;
            }

            const card = document.createElement('div');
            card.className = `event-card animate-fade-in-up stagger-${(index % 3) + 1}`;
            card.innerHTML = `
                <div class="event-banner">
                    <img src="${ev.image}" alt="${ev.title}">
                    <div class="event-badges">
                        <span class="event-category ${badgeClass}">${ev.category}</span>
                        ${isFull ? '<span class="event-status bg-danger text-white border border-danger">Full</span>' : ''}
                    </div>
                </div>
                <div class="event-body">
                    <h3 class="event-title">${ev.title}</h3>
                    <p class="event-desc">${ev.description}</p>
                    
                    <ul class="event-info">
                        <li><i class="bi bi-calendar3"></i> <span>${ev.dateStr} <br><small class="text-muted">${ev.timeStr}</small></span></li>
                        <li><i class="bi bi-geo-alt"></i> <span>${ev.location}</span></li>
                    </ul>

                    <div class="slots-container mt-auto">
                        <div class="slots-header">
                            <span>${ev.slotsFilled} Joined</span>
                            <span>${ev.slotsTotal - ev.slotsFilled} Spots Left</span>
                        </div>
                        <div class="slots-progress">
                            <div class="slots-bar ${isFull ? 'full' : ''}" style="width: ${progressPct}%"></div>
                        </div>
                    </div>
                    
                    <!-- Timer Container -->
                    <div class="countdown-timer" data-timestamp="${ev.timestamp}">
                        <div class="countdown-block"><span class="countdown-val d">-</span><span class="countdown-label">Days</span></div>
                        <div class="countdown-block text-muted mt-1">:</div>
                        <div class="countdown-block"><span class="countdown-val h">-</span><span class="countdown-label">Hrs</span></div>
                        <div class="countdown-block text-muted mt-1">:</div>
                        <div class="countdown-block"><span class="countdown-val m">-</span><span class="countdown-label">Min</span></div>
                        <div class="countdown-block text-muted mt-1">:</div>
                        <div class="countdown-block"><span class="countdown-val s">-</span><span class="countdown-label">Sec</span></div>
                    </div>

                    <div class="event-footer mt-2">
                        <button class="btn ${btnClass} w-100 rounded-pill fw-semibold request-btn" data-id="${ev.id}" ${isDisabled ? 'disabled' : ''}>
                            ${btnText}
                        </button>
                    </div>
                </div>
            `;
            gridEl.appendChild(card);
        });

        // Add event listeners to request buttons
        document.querySelectorAll('.request-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const eventId = e.target.getAttribute('data-id');
                e.target.disabled = true;
                const originalText = e.target.innerHTML;
                e.target.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
                
                try {
                    const res = await (window.api ? window.api.post('/requests', { event_id: eventId }) : fetch('/api/requests', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                        },
                        body: JSON.stringify({ event_id: eventId })
                    }).then(r => r.json()));
                    
                    const data = window.api ? res.data : res;
                    
                    if (data.status === 'success') {
                        e.target.innerHTML = 'Requested';
                        e.target.classList.replace('btn-primary', 'btn-success');
                        if (window.showToast) showToast('Success', data.message || 'Request submitted successfully!', 'success');
                    } else {
                        e.target.disabled = false;
                        e.target.innerHTML = originalText;
                        if (window.showToast) showToast('Notice', data.message || 'You may have already requested this event.', 'warning');
                    }
                } catch (error) {
                    e.target.disabled = false;
                    e.target.innerHTML = originalText;
                    if (window.showToast) showToast('Error', 'Failed to submit request. Please try again.', 'danger');
                }
            });
        });

        startTimers();
        renderPagination(filteredEvents.length, Math.ceil(filteredEvents.length / itemsPerPage));
    }

    function renderSkeletons() {
        gridEl.innerHTML = '';
        for (let i = 0; i < 6; i++) {
            gridEl.innerHTML += `
                <div class="event-card skeleton-card skeleton">
                    <div class="event-banner"></div>
                    <div class="event-body">
                        <div class="event-title"></div>
                        <div class="event-desc"></div>
                        <ul class="event-info"><li></li><li></li></ul>
                        <div class="mt-auto pt-3"><div class="btn"></div></div>
                    </div>
                </div>
            `;
        }
        paginationEl.innerHTML = '';
    }

    // ==========================================
    // Pagination
    // ==========================================
    function renderPagination(totalItems, totalPages) {
        paginationEl.innerHTML = '';
        if (totalPages <= 1) return;

        let html = `<ul class="pagination justify-content-center mb-0">`;
        
        // Prev
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                    <a class="page-link border-0 shadow-sm rounded-circle mx-1" href="#" data-page="${currentPage - 1}"><i class="bi bi-chevron-left"></i></a>
                 </li>`;
        
        // Pages
        for (let i = 1; i <= totalPages; i++) {
            html += `<li class="page-item ${currentPage === i ? 'active' : ''}">
                        <a class="page-link border-0 shadow-sm rounded-circle mx-1" href="#" data-page="${i}">${i}</a>
                     </li>`;
        }
        
        // Next
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                    <a class="page-link border-0 shadow-sm rounded-circle mx-1" href="#" data-page="${currentPage + 1}"><i class="bi bi-chevron-right"></i></a>
                 </li>`;
        
        html += `</ul>`;
        paginationEl.innerHTML = html;

        // Bind clicks
        paginationEl.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = parseInt(e.currentTarget.getAttribute('data-page'));
                if (!isNaN(target) && target >= 1 && target <= totalPages) {
                    currentPage = target;
                    renderGrid();
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        });
    }

    // ==========================================
    // Countdown Timer Logic
    // ==========================================
    function startTimers() {
        const timerEls = document.querySelectorAll('.countdown-timer');
        if (timerEls.length === 0) return;

        function update() {
            const now = new Date().getTime();
            timerEls.forEach(el => {
                const target = parseInt(el.getAttribute('data-timestamp'));
                const diff = target - now;

                if (diff < 0) {
                    el.innerHTML = `<div class="text-success fw-bold w-100 text-center"><i class="bi bi-check2-circle me-1"></i>Event Started / Ended</div>`;
                    return;
                }

                const d = Math.floor(diff / (1000 * 60 * 60 * 24));
                const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const s = Math.floor((diff % (1000 * 60)) / 1000);

                const dEl = el.querySelector('.d');
                const hEl = el.querySelector('.h');
                const mEl = el.querySelector('.m');
                const sEl = el.querySelector('.s');
                
                if(dEl) dEl.textContent = d.toString().padStart(2, '0');
                if(hEl) hEl.textContent = h.toString().padStart(2, '0');
                if(mEl) mEl.textContent = m.toString().padStart(2, '0');
                if(sEl) sEl.textContent = s.toString().padStart(2, '0');
            });
        }

        update(); // Initial call
        timerInterval = setInterval(update, 1000);
    }

    // ==========================================
    // Utils
    // ==========================================
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // ==========================================
    // Map Logic
    // ==========================================
    function switchView(view) {
        if (view === 'map') {
            isMapView = true;
            btnMapView.classList.add('active');
            btnListView.classList.remove('active');
            gridEl.style.display = 'none';
            paginationEl.style.display = 'none';
            mapContainer.style.display = 'block';
            if (userLat !== null) {
                distanceFilterContainer.classList.remove('d-none');
            }
            renderMap();
        } else {
            isMapView = false;
            btnListView.classList.add('active');
            btnMapView.classList.remove('active');
            mapContainer.style.display = 'none';
            gridEl.style.display = 'flex';
            paginationEl.style.display = 'flex';
            distanceFilterContainer.classList.add('d-none');
            renderGrid();
        }
    }

    function renderMap() {
        if (!map) {
            map = L.map('mapContainer').setView([20.5937, 78.9629], 5); // Default to India
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            markersLayer = L.layerGroup().addTo(map);
        }
        
        // Fix map rendering issues if container was hidden
        setTimeout(() => map.invalidateSize(), 100);

        markersLayer.clearLayers();
        let hasMarkers = false;
        const bounds = L.latLngBounds();

        const now = new Date().getTime();
        filteredEvents.forEach(ev => {
            const isPast = ev.timestamp < now;
            if (isPast) return; // Do not show past events on the map

            if (ev.geo && ev.geo.coordinates) {
                const lng = ev.geo.coordinates[0];
                const lat = ev.geo.coordinates[1];
                hasMarkers = true;
                bounds.extend([lat, lng]);

                const marker = L.marker([lat, lng]).addTo(markersLayer);
                
                const popupContent = `
                    <div style="width: 220px;">
                        <img src="${ev.image}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 8px 8px 0 0;">
                        <div class="p-2">
                            <span class="badge bg-primary mb-1">${ev.category}</span>
                            <h6 class="fw-bold mb-1">${ev.title}</h6>
                            <p class="mb-1 small"><i class="bi bi-calendar3"></i> ${ev.dateStr}</p>
                            <p class="mb-2 small"><i class="bi bi-geo-alt"></i> ${ev.location}</p>
                            <button class="btn btn-sm btn-outline-primary w-100" onclick="window.requestEventJoin(this, '${ev.id}')">Join Event</button>
                        </div>
                    </div>
                `;
                marker.bindPopup(popupContent, { padding: 0 });
            }
        });

        if (hasMarkers && userLat === null) {
            map.fitBounds(bounds, { padding: [50, 50] });
        } else if (userLat !== null) {
            map.setView([userLat, userLng], 11);
            // Add user location marker
            L.circleMarker([userLat, userLng], {
                color: '#0d6efd',
                fillColor: '#0d6efd',
                fillOpacity: 0.5,
                radius: 8
            }).addTo(markersLayer).bindPopup("<b>Your Location</b>");
        }
    }

    function handleNearMe() {
        const originalText = btnNearMe.innerHTML;
        btnNearMe.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Locating...';
        btnNearMe.disabled = true;

        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition((position) => {
                userLat = position.coords.latitude;
                userLng = position.coords.longitude;
                btnNearMe.innerHTML = '<i class="bi bi-check-circle me-1"></i> Location Active';
                btnNearMe.classList.replace('btn-primary', 'btn-success');
                btnNearMe.disabled = false;
                
                if (isMapView) distanceFilterContainer.classList.remove('d-none');
                
                fetchEvents();
                if (!isMapView) switchView('map');
            }, (error) => {
                console.error("Error getting location:", error);
                btnNearMe.innerHTML = originalText;
                btnNearMe.disabled = false;
                if (window.showToast) showToast('Error', 'Could not get your precise location. Please ensure location permissions are granted.', 'danger');
            }, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            });
        } else {
            btnNearMe.innerHTML = originalText;
            btnNearMe.disabled = false;
            if (window.showToast) showToast('Error', 'Geolocation is not supported by your browser.', 'danger');
        }
    }

});

// Global function to handle map popup joins
window.requestEventJoin = async function(btn, eventId) {
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    
    try {
        const res = await (window.api ? window.api.post('/requests', { event_id: eventId }) : fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
            },
            body: JSON.stringify({ event_id: eventId })
        }).then(r => r.json()));
        
        const data = window.api ? res.data : res;
        
        if (data.status === 'success') {
            btn.innerHTML = 'Requested';
            btn.classList.replace('btn-outline-primary', 'btn-success');
            btn.classList.remove('btn-outline-primary');
            btn.classList.add('text-white');
            if (window.showToast) window.showToast('Success', data.message || 'Request submitted successfully!', 'success');
        } else {
            btn.disabled = false;
            btn.innerHTML = originalText;
            if (window.showToast) window.showToast('Notice', data.message || 'Failed to submit request.', 'warning');
        }
    } catch (error) {
        btn.disabled = false;
        btn.innerHTML = originalText;
        if (window.showToast) window.showToast('Error', 'Failed to submit request.', 'danger');
    }
};
