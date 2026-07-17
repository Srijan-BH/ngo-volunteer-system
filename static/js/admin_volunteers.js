/**
 * Admin Volunteers Directory Logic
 * Handles fetching, filtering, profile modals, and data export.
 */

document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.getElementById('volunteersTbody');
    const searchInput = document.getElementById('volunteerSearch');
    const statusFilter = document.getElementById('statusFilter');
    const availabilityFilter = document.getElementById('availabilityFilter');
    const exportBtn = document.getElementById('exportBtn');
    
    let currentPage = 1;

    // ==========================================
    // Fetch & Render
    // ==========================================
    async function fetchVolunteers(page = 1) {
        currentPage = page;
        if (!tbody) return;
        
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5"><div class="spinner-border text-primary"></div></td></tr>`;
        
        try {
            const params = new URLSearchParams({ page: page, page_size: 10 });
            if (statusFilter.value) params.append('status', statusFilter.value);
            if (availabilityFilter.value) params.append('availability', availabilityFilter.value);
            // Simulating search on frontend or backend depending on API
            
            const response = await fetch(`/api/volunteers?${params.toString()}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}` }
            });
            
            if (!response.ok) throw new Error('API Error');

            const data = await response.json();
            if (data.status === 'success') {
                let vols = data.data.items;
                if (searchInput.value) {
                    const q = searchInput.value.toLowerCase();
                    vols = vols.filter(v => v.user?.name.toLowerCase().includes(q) || v.user?.email.toLowerCase().includes(q));
                }
                renderVolunteers(vols);
                if (data.meta) renderPagination(data.meta);
            }
        } catch (error) {
            console.warn('Failed to fetch from API', error);
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Failed to load volunteers.</td></tr>`;
        }
    }

    function renderVolunteers(volunteers) {
        tbody.innerHTML = '';

        if (volunteers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <i class="bi bi-people-fill display-4 text-muted mb-3 d-block"></i>
                        <h5 class="fw-bold">No volunteers found</h5>
                        <p class="text-muted mb-0">Try adjusting your filters or search query.</p>
                    </td>
                </tr>
            `;
            return;
        }

        volunteers.forEach((vol, index) => {
            const name = vol.user?.name || vol.name || 'Unknown User';
            const email = vol.user?.email || vol.email || 'No email provided';
            const avatar = vol.user?.profile_picture ? `/uploads/${vol.user.profile_picture}` : `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random`;
            const statusClass = `status-${vol.status || 'pending'}`;
            
            let skillsHtml = '';
            if (vol.skills && vol.skills.length > 0) {
                // Show max 3 skills
                vol.skills.slice(0, 3).forEach(s => {
                    skillsHtml += `<span class="skill-tag">${s}</span>`;
                });
                if (vol.skills.length > 3) skillsHtml += `<span class="skill-tag">+${vol.skills.length - 3}</span>`;
            } else {
                skillsHtml = '<span class="text-muted small">None listed</span>';
            }

            const tr = document.createElement('tr');
            tr.className = `animate-fade-in-up stagger-${(index % 4) + 1}`;
            tr.innerHTML = `
                <td>
                    <div class="user-info-cell">
                        <img src="${avatar}" alt="Avatar" class="user-avatar">
                        <div class="user-details">
                            <span class="user-name">${name}</span>
                            <span class="user-email">${email}</span>
                        </div>
                    </div>
                </td>
                <td><span class="status-badge ${statusClass}">${vol.status || 'Pending'}</span></td>
                <td>${vol.location || 'Not set'}</td>
                <td class="text-capitalize">${vol.availability || 'Any'}</td>
                <td>
                    <div class="skill-tags">${skillsHtml}</div>
                </td>
                <td class="fw-semibold">${vol.hours_contributed || 0}h</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-sm btn-outline-primary rounded-circle view-profile" data-id="${vol.id || vol._id}" title="View Profile">
                            <i class="bi bi-eye"></i>
                        </button>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary rounded-circle" type="button" data-bs-toggle="dropdown">
                                <i class="bi bi-three-dots-vertical"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow">
                                <li><a class="dropdown-item status-change" href="#" data-id="${vol.id || vol._id}" data-status="active">Set Active</a></li>
                                <li><a class="dropdown-item status-change" href="#" data-id="${vol.id || vol._id}" data-status="inactive">Set Inactive</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#">Delete Volunteer</a></li>
                            </ul>
                        </div>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        attachActionListeners();
    }

    function renderMockVolunteers() {
        const mockData = [
            { _id: '1', name: 'Alice Smith', email: 'alice@example.com', status: 'active', location: 'New York', availability: 'weekends', skills: ['First Aid', 'Teaching', 'Event Planning'], hours_contributed: 45 },
            { _id: '2', name: 'Bob Jones', email: 'bob@example.com', status: 'inactive', location: 'Chicago', availability: 'any', skills: ['Driving'], hours_contributed: 12 },
            { _id: '3', name: 'Charlie Davis', email: 'charlie@example.com', status: 'active', location: 'San Francisco', availability: 'weekdays', skills: ['Social Media', 'Writing', 'Photography', 'Design'], hours_contributed: 120 }
        ];
        
        let filtered = mockData;
        if (statusFilter.value) filtered = filtered.filter(v => v.status === statusFilter.value);
        if (availabilityFilter.value) filtered = filtered.filter(v => v.availability === availabilityFilter.value);
        if (searchInput.value) {
            const q = searchInput.value.toLowerCase();
            filtered = filtered.filter(v => v.name.toLowerCase().includes(q) || v.email.toLowerCase().includes(q));
        }
        
        renderVolunteers(filtered);
    }

    // ==========================================
    // Actions & Listeners
    // ==========================================
    function attachActionListeners() {
        // Status Change
        document.querySelectorAll('.status-change').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const id = e.currentTarget.getAttribute('data-id');
                const status = e.currentTarget.getAttribute('data-status');
                
                try {
                    await fetch(`/api/volunteers/${id}/status`, { 
                        method: 'PATCH',
                        headers: { 
                            'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ status })
                    });
                    showToast('Success', `Status updated to ${status}`, 'success');
                    fetchVolunteers(currentPage);
                } catch(err) {
                    showToast('Error', `Failed to update status`, 'danger');
                    fetchVolunteers(currentPage);
                }
            });
        });

        // View Profile Modal
        const profileModalEl = document.getElementById('profileModal');
        if (!profileModalEl) return;
        const profileModal = bootstrap.Modal.getOrCreateInstance(profileModalEl);

        document.querySelectorAll('.view-profile').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const row = e.currentTarget.closest('tr');
                const name = row.querySelector('.user-name').innerText;
                const email = row.querySelector('.user-email').innerText;
                const avatar = row.querySelector('.user-avatar').src;
                const location = row.children[2].innerText;
                const availability = row.children[3].innerText;
                const hours = row.children[5].innerText;
                const skillsHtml = row.children[4].innerHTML;
                const statusBadge = row.children[1].innerHTML;
                
                const modalBody = document.getElementById('profileModalBody');
                modalBody.innerHTML = `
                    <div class="mb-4">
                        <img src="${avatar}" alt="Avatar" class="rounded-circle mb-3 shadow" style="width: 90px; height: 90px; object-fit: cover; border: 3px solid var(--accent-primary, #6366f1);">
                        <h4 class="fw-bold mb-1">${name}</h4>
                        <p class="text-muted small mb-2">${email}</p>
                        <div>${statusBadge}</div>
                    </div>
                    <div class="text-start p-3 rounded-3" style="background: var(--bg-secondary, #f8f9fa); border: 1px solid var(--border-color, #e5e7eb);">
                        <div class="row g-3">
                            <div class="col-6">
                                <div class="text-muted small fw-semibold mb-1"><i class="bi bi-geo-alt me-1"></i>Location</div>
                                <div class="fw-medium">${location}</div>
                            </div>
                            <div class="col-6">
                                <div class="text-muted small fw-semibold mb-1"><i class="bi bi-calendar-check me-1"></i>Availability</div>
                                <div class="fw-medium text-capitalize">${availability}</div>
                            </div>
                            <div class="col-12">
                                <div class="text-muted small fw-semibold mb-1"><i class="bi bi-clock-history me-1"></i>Volunteer Hours</div>
                                <div class="fw-medium">${hours === '0h' ? 'New volunteer — no hours yet' : hours}</div>
                            </div>
                            <div class="col-12">
                                <div class="text-muted small fw-semibold mb-1"><i class="bi bi-tools me-1"></i>Skills</div>
                                <div class="mt-1">${skillsHtml}</div>
                            </div>
                        </div>
                    </div>
                `;

                // Wire up contact button
                const contactBtn = document.getElementById('contactVolunteerBtn');
                if (contactBtn) {
                    contactBtn.href = 'mailto:' + email;
                }
                
                profileModal.show();
            });
        });
    }

    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => fetchVolunteers(1), 500);
        });
    }

    if (statusFilter) statusFilter.addEventListener('change', () => fetchVolunteers(1));
    if (availabilityFilter) availabilityFilter.addEventListener('change', () => fetchVolunteers(1));
    
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            showToast('Export Started', 'Your CSV file is being generated and will download shortly.', 'info');
            try {
                const res = await fetch('/api/volunteers/export', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}` }
                });
                
                if (res.ok) {
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'volunteers_export.csv';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                    showToast('Export Complete', 'Your CSV file has been downloaded successfully.', 'success');
                } else {
                    showToast('Export Failed', 'Failed to generate CSV file.', 'danger');
                }
            } catch (err) {
                console.error("Export error", err);
                showToast('Export Error', 'An error occurred during export.', 'danger');
            }
        });
    }

    function showToast(title, message, type='primary') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;
        const toastId = 'toast-' + Date.now();
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body"><strong>${title}</strong><br>${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>`;
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(toastId);
        new bootstrap.Toast(toastEl, { delay: 3000 }).show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    function renderPagination(meta) {
        const ul = document.getElementById('volunteersPagination');
        if(!ul) return;
        ul.innerHTML = '';
        for(let i=1; i<=meta.total_pages; i++){
            ul.innerHTML += `<li class="page-item ${i === meta.page ? 'active' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); window.fetchVolunteers(${i})">${i}</a></li>`;
        }
    }
    window.fetchVolunteers = fetchVolunteers;

    if (tbody) fetchVolunteers(1);
});
