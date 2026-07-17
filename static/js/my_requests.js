/**
 * My Requests JavaScript
 * Fetches and displays the user's event join requests.
 */

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('requestsContainer');
    const tabs = document.querySelectorAll('#requestsTabs button');
    const paginationInfo = document.getElementById('paginationInfo');
    const paginationControls = document.getElementById('paginationControls');
    
    let currentStatus = '';
    let currentPage = 1;
    const pageSize = 10;

    // Initialize tabs
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            currentStatus = e.target.getAttribute('data-status');
            currentPage = 1; // reset on tab change
            fetchRequests();
        });
    });

    async function fetchRequests() {
        renderSkeletons();

        let url = `/api/requests/my-requests?page=${currentPage}&page_size=${pageSize}`;
        if (currentStatus) {
            url += `&status=${currentStatus}`;
        }

        try {
            const res = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                }
            });

            if (!res.ok) throw new Error('Failed to fetch');

            const data = await res.json();
            if (data.status === 'success') {
                renderRequests(data.data || []);
                renderPagination(data.meta);
            }
        } catch (error) {
            console.error('Error fetching requests:', error);
            container.innerHTML = `
                <div class="col-12 text-center py-5">
                    <i class="bi bi-exclamation-triangle text-danger" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">Failed to load requests</h5>
                    <p class="text-muted">Please try again later.</p>
                </div>
            `;
        }
    }

    function renderSkeletons() {
        container.innerHTML = '';
        for (let i = 0; i < 3; i++) {
            container.innerHTML += `
                <div class="col-12 mb-3">
                    <div class="card bg-tertiary border-0 shadow-sm p-4 skeleton">
                        <div class="skeleton-text skeleton-title mb-2"></div>
                        <div class="skeleton-text"></div>
                    </div>
                </div>
            `;
        }
    }

    function renderRequests(requests) {
        container.innerHTML = '';

        if (requests.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center py-5 animate-fade-in-up">
                    <i class="bi bi-inbox text-muted" style="font-size: 4rem;"></i>
                    <h4 class="mt-3 fw-bold text-muted">No Requests Found</h4>
                    <p class="text-muted">You have no requests matching this filter.</p>
                </div>
            `;
            return;
        }

        requests.forEach((req, idx) => {
            const event = req.event || {};
            const statusBadge = getStatusBadge(req.status);
            
            // Format Dates
            const appliedDate = req.applied_date ? new Date(req.applied_date).toLocaleDateString() : 'N/A';
            const eventDate = event.date ? new Date(event.date).toLocaleDateString() : 'N/A';

            let actionButton = '';
            if (req.status === 'pending' || req.status === 'approved') {
                actionButton = `<button class="btn btn-outline-danger btn-sm rounded-pill ms-auto withdraw-btn" data-id="${req.id}"><i class="bi bi-x-circle me-1"></i> Withdraw</button>`;
            }

            container.innerHTML += `
                <div class="col-12 mb-3 animate-fade-in-up stagger-${(idx % 4) + 1}">
                    <div class="card bg-tertiary border-0 shadow-sm h-100">
                        <div class="card-body d-flex flex-column flex-md-row justify-content-between align-items-md-center">
                            <div class="mb-3 mb-md-0">
                                <h5 class="fw-bold mb-1">${event.title || 'Unknown Event'}</h5>
                                <div class="text-muted small mb-2">
                                    <i class="bi bi-calendar-event me-1"></i> Event Date: ${eventDate} 
                                    <span class="mx-2">•</span> 
                                    <i class="bi bi-clock me-1"></i> Applied: ${appliedDate}
                                </div>
                                <div class="d-flex align-items-center mt-2">
                                    ${statusBadge}
                                    ${req.remarks ? `<span class="ms-3 text-muted small"><i class="bi bi-chat-quote-fill me-1"></i> "${req.remarks}"</span>` : ''}
                                </div>
                            </div>
                            <div class="d-flex align-items-center">
                                ${actionButton}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        // Attach withdraw listeners
        document.querySelectorAll('.withdraw-btn').forEach(btn => {
            btn.addEventListener('click', handleWithdraw);
        });
    }

    function getStatusBadge(status) {
        switch (status) {
            case 'pending': return `<span class="badge bg-warning text-dark px-3 py-2 rounded-pill"><i class="bi bi-hourglass-split me-1"></i> Pending</span>`;
            case 'approved': return `<span class="badge bg-success px-3 py-2 rounded-pill"><i class="bi bi-check-circle me-1"></i> Approved</span>`;
            case 'rejected': return `<span class="badge bg-danger px-3 py-2 rounded-pill"><i class="bi bi-x-circle me-1"></i> Rejected</span>`;
            case 'withdrawn': return `<span class="badge bg-secondary px-3 py-2 rounded-pill"><i class="bi bi-dash-circle me-1"></i> Withdrawn</span>`;
            case 'attended': return `<span class="badge bg-info text-dark px-3 py-2 rounded-pill"><i class="bi bi-patch-check me-1"></i> Attended</span>`;
            case 'no_show': return `<span class="badge bg-dark px-3 py-2 rounded-pill"><i class="bi bi-person-x me-1"></i> No Show</span>`;
            default: return `<span class="badge bg-secondary px-3 py-2 rounded-pill">${status}</span>`;
        }
    }

    function renderPagination(meta) {
        const start = (meta.page - 1) * meta.page_size + 1;
        const end = Math.min(meta.page * meta.page_size, meta.total);
        
        if (meta.total === 0) {
            paginationInfo.textContent = 'Showing 0-0 of 0 requests';
            paginationControls.innerHTML = '';
            return;
        }

        paginationInfo.textContent = `Showing ${start}-${end} of ${meta.total} requests`;

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
                fetchRequests();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }

    async function handleWithdraw(e) {
        const id = e.currentTarget.getAttribute('data-id');
        if (!confirm('Are you sure you want to withdraw this request? This action cannot be undone.')) {
            return;
        }

        const btn = e.currentTarget;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Withdrawing...`;

        try {
            const res = await fetch(`/api/requests/${id}/withdraw`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                }
            });

            if (!res.ok) throw new Error('Failed to withdraw');
            
            // Refresh the current view
            fetchRequests();
            
        } catch (error) {
            console.error('Error withdrawing:', error);
            alert('An error occurred while withdrawing the request.');
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-x-circle me-1"></i> Withdraw`;
        }
    }

    // Initial load
    fetchRequests();
});
