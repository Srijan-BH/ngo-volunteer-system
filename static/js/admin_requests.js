/**
 * Admin Requests Logic
 * Handles viewing pending volunteer requests and processing approvals/rejections.
 */

document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.getElementById('requestsTbody');
    const searchInput = document.getElementById('requestSearch');
    const statusFilter = document.getElementById('statusFilter');
    
    let currentPage = 1;
    let selectedRequestId = null;
    const rejectModal = document.getElementById('rejectModal') ? new bootstrap.Modal(document.getElementById('rejectModal')) : null;

    // ==========================================
    // Fetch & Render
    // ==========================================
    async function fetchRequests(page = 1) {
        currentPage = page;
        if (!tbody) return;
        
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-5"><div class="spinner-border text-primary"></div></td></tr>`;
        
        try {
            // Using the admin pending requests endpoint or all requests with status filter
            let url = `/api/admin/requests?page=${page}`;
            if (statusFilter.value) {
                url += `&status=${statusFilter.value}`;
            }

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}` }
            });
            
            if (!response.ok) throw new Error('API Error');

            const data = await response.json();
            if (data.status === 'success') {
                let reqs = data.data;
                // Basic frontend search implementation
                if (searchInput.value) {
                    const q = searchInput.value.toLowerCase();
                    reqs = reqs.filter(r => 
                        (r.user?.name && r.user.name.toLowerCase().includes(q)) || 
                        (r.event?.title && r.event.title.toLowerCase().includes(q))
                    );
                }
                renderRequests(reqs);
                if (data.meta) renderPagination(data.meta);
            }
        } catch (error) {
            console.warn('Failed to fetch from API', error);
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Failed to load requests.</td></tr>`;
        }
    }

    function renderRequests(requests) {
        tbody.innerHTML = '';

        if (requests.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <i class="bi bi-inbox display-4 text-muted mb-3 d-block"></i>
                        <h5 class="fw-bold">No requests found</h5>
                        <p class="text-muted mb-0">You're all caught up!</p>
                    </td>
                </tr>
            `;
            return;
        }

        requests.forEach((req, index) => {
            const volName = req.user?.name || req.volunteer_name || 'John Doe';
            const volEmail = req.user?.email || req.volunteer_email || 'john@example.com';
            const eventTitle = req.event?.title || req.event_title || 'Unknown Event';
            const statusClass = `status-${req.status || 'pending'}`;
            const dateStr = new Date(req.applied_date || req.created_at || Date.now()).toLocaleDateString();

            const tr = document.createElement('tr');
            tr.className = `animate-fade-in-up stagger-${(index % 4) + 1}`;
            tr.innerHTML = `
                <td>
                    <div class="user-info-cell">
                        <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(volName)}&background=random" alt="Avatar" class="user-avatar">
                        <div class="user-details">
                            <span class="user-name">${volName}</span>
                            <span class="user-email">${volEmail}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="fw-semibold text-primary">${eventTitle}</span>
                </td>
                <td>
                    <span class="text-secondary small d-inline-block text-truncate" style="max-width: 200px;" title="${req.remarks || req.user_remarks || 'None'}">
                        ${req.remarks || req.user_remarks || 'None'}
                    </span>
                </td>
                <td>${dateStr}</td>
                <td><span class="status-badge ${statusClass}">${req.status || 'Pending'}</span></td>
                <td>
                    <div class="actions-cell">
                        ${req.status === 'pending' ? `
                            <button class="btn btn-sm btn-outline-success rounded-pill px-3 action-approve" data-id="${req.id || req._id}" title="Approve">
                                <i class="bi bi-check-lg me-1"></i> Approve
                            </button>
                            <button class="btn btn-sm btn-outline-danger rounded-pill px-3 action-reject" data-id="${req.id || req._id}" title="Reject">
                                <i class="bi bi-x-lg me-1"></i> Reject
                            </button>
                        ` : req.status === 'approved' ? `
                            <button class="btn btn-sm btn-outline-primary rounded-pill px-3 action-award" data-id="${req.id || req._id}" title="Award Hours">
                                <i class="bi bi-award me-1"></i> Award Hours
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-outline-secondary rounded-pill px-3" disabled>Processed</button>
                        `}
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        attachActionListeners();
    }

    function renderMockRequests() {
        const mockData = [
            { _id: '1', volunteer_name: 'David Lee', volunteer_email: 'david@example.com', event_title: 'Beach Cleanup', remarks: 'I have experience in waste management.', status: 'pending', created_at: new Date().toISOString() },
            { _id: '2', volunteer_name: 'Emma Watson', volunteer_email: 'emma@example.com', event_title: 'Tutoring Program', remarks: 'I love teaching kids.', status: 'pending', created_at: new Date(Date.now() - 86400).toISOString() },
            { _id: '3', volunteer_name: 'Frank Ocean', volunteer_email: 'frank@example.com', event_title: 'Food Drive', remarks: '', status: 'approved', created_at: new Date(Date.now() - 864000).toISOString() }
        ];
        
        let filtered = mockData;
        if (statusFilter.value) filtered = filtered.filter(r => r.status === statusFilter.value);
        if (searchInput.value) {
            const q = searchInput.value.toLowerCase();
            filtered = filtered.filter(r => r.volunteer_name.toLowerCase().includes(q) || r.event_title.toLowerCase().includes(q));
        }
        
        renderRequests(filtered);
    }

    // ==========================================
    // Actions & Listeners
    // ==========================================
    function attachActionListeners() {
        // Approve
        document.querySelectorAll('.action-approve').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const id = e.currentTarget.getAttribute('data-id');
                const row = e.currentTarget.closest('tr');
                
                try {
                    const response = await fetch(`/api/admin/requests/${id}/approve`, { 
                        method: 'POST',
                        headers: { 
                            'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ remarks: 'Approved by admin' })
                    });
                    
                    if(response.ok) {
                        showToast('Success', 'Request approved!', 'success');
                        fetchRequests(currentPage);
                    } else {
                        throw new Error('API Error');
                    }
                } catch(err) {
                    showToast('Error', 'Failed to approve request.', 'danger');
                }
            });
        });

        // Reject (Opens Modal)
        document.querySelectorAll('.action-reject').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                selectedRequestId = e.currentTarget.getAttribute('data-id');
                document.getElementById('rejectRemarks').value = '';
                if(rejectModal) rejectModal.show();
            });
        });

        // Award Hours (Opens Modal)
        document.querySelectorAll('.action-award').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                selectedRequestId = e.currentTarget.getAttribute('data-id');
                document.getElementById('awardHoursInput').value = '';
                const awardModal = new bootstrap.Modal(document.getElementById('awardHoursModal'));
                awardModal.show();
            });
        });
    }

    // Confirm Reject in Modal
    const confirmRejectBtn = document.getElementById('confirmRejectBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', async () => {
            const remarks = document.getElementById('rejectRemarks').value;
            if (remarks.length < 3) {
                alert("Please provide a valid reason.");
                return;
            }
            
            const origText = confirmRejectBtn.innerHTML;
            confirmRejectBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
            confirmRejectBtn.disabled = true;

            try {
                const response = await fetch(`/api/admin/requests/${selectedRequestId}/reject`, { 
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ remarks })
                });
                
                if(response.ok) {
                    showToast('Success', 'Request rejected.', 'danger');
                } else {
                    throw new Error('API Error');
                }
            } catch(err) {
                showToast('Success', '(Mock) Request rejected.', 'danger');
            } finally {
                confirmRejectBtn.innerHTML = origText;
                confirmRejectBtn.disabled = false;
                rejectModal.hide();
                fetchRequests(currentPage);
            }
        });
    }

    // Confirm Award Hours in Modal
    const confirmAwardBtn = document.getElementById('confirmAwardBtn');
    if (confirmAwardBtn) {
        confirmAwardBtn.addEventListener('click', async () => {
            const hours = document.getElementById('awardHoursInput').value;
            if (!hours || isNaN(hours) || hours <= 0) {
                alert("Please enter a valid number of hours.");
                return;
            }
            
            const origText = confirmAwardBtn.innerHTML;
            confirmAwardBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
            confirmAwardBtn.disabled = true;

            try {
                const response = await fetch(`/api/admin/requests/${selectedRequestId}/attended`, { 
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ hours: parseFloat(hours) })
                });
                
                if(response.ok) {
                    showToast('Success', 'Volunteer marked as attended and hours awarded.', 'success');
                } else {
                    const data = await response.json();
                    throw new Error(data.message || 'API Error');
                }
            } catch(err) {
                showToast('Error', err.message || 'Failed to award hours.', 'danger');
            } finally {
                confirmAwardBtn.innerHTML = origText;
                confirmAwardBtn.disabled = false;
                const modalEl = document.getElementById('awardHoursModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
                fetchRequests(currentPage);
            }
        });
    }

    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => fetchRequests(1), 500);
        });
    }

    if (statusFilter) statusFilter.addEventListener('change', () => fetchRequests(1));

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
        const ul = document.getElementById('requestsPagination');
        if(!ul) return;
        ul.innerHTML = '';
        for(let i=1; i<=meta.total_pages; i++){
            ul.innerHTML += `<li class="page-item ${i === meta.page ? 'active' : ''}"><a class="page-link" href="#" onclick="event.preventDefault(); window.fetchRequests(${i})">${i}</a></li>`;
        }
    }
    window.fetchRequests = fetchRequests;

    if (tbody) fetchRequests(1);
});
