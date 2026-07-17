/**
 * Admin Events Management Script
 */
document.addEventListener('DOMContentLoaded', () => {
    fetchEvents();

    const evIsVirtual = document.getElementById('evIsVirtual');
    if (evIsVirtual) {
        evIsVirtual.addEventListener('change', (e) => {
            const locContainer = document.getElementById('locationContainer');
            const addrContainer = document.getElementById('addressContainer');
            const meetContainer = document.getElementById('meetingLinkContainer');
            
            if (e.target.checked) {
                locContainer.classList.add('d-none');
                addrContainer.classList.add('d-none');
                meetContainer.classList.remove('d-none');
            } else {
                locContainer.classList.remove('d-none');
                addrContainer.classList.remove('d-none');
                meetContainer.classList.add('d-none');
            }
        });
    }

    const btnSubmit = document.getElementById('btnSubmitEvent');
    if (btnSubmit) {
        btnSubmit.addEventListener('click', handleCreateEvent);
    }

    // Initialize Flatpickr for 12-hour AM/PM datetime selection
    if (window.flatpickr) {
        flatpickr("#evStartDate", {
            enableTime: true,
            allowInput: true,
            altInput: true,
            altFormat: "F j, Y h:i K", // e.g., July 1, 2026 02:30 PM
            dateFormat: "Y-m-d\\TH:i", // Standard ISO format for backend
            time_24hr: false,
            minDate: "today"
        });
        flatpickr("#evEndDate", {
            enableTime: true,
            allowInput: true,
            altInput: true,
            altFormat: "F j, Y h:i K",
            dateFormat: "Y-m-d\\TH:i",
            time_24hr: false,
            minDate: "today"
        });
    }
});

function getAuthToken() {
    return localStorage.getItem('admin_access_token');
}

let editingEventId = null;
let currentEvents = [];

async function fetchEvents(page = 1) {
    const upcomingTable = document.getElementById('upcomingEventsTableBody');
    const pastTable = document.getElementById('pastEventsTableBody');
    if (upcomingTable) upcomingTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm text-primary me-2"></div>Loading upcoming events...</td></tr>';
    if (pastTable) pastTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm text-primary me-2"></div>Loading past events...</td></tr>';
    
    try {
        const token = getAuthToken();
        const res = await fetch(`/api/events?page=${page}&page_size=20`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            currentEvents = data.data.items;
            renderEventsTable(currentEvents);
            const totalItems = data.data.pagination ? data.data.pagination.total_items : currentEvents.length;
            document.getElementById('eventsCountText').textContent = `Showing ${currentEvents.length} of ${totalItems} events`;
            // Simple pagination rendering could go here
        } else {
            if (upcomingTable) upcomingTable.innerHTML = `<tr><td colspan="7" class="text-center text-danger">${data.message || 'Failed to load events'}</td></tr>`;
            if (pastTable) pastTable.innerHTML = `<tr><td colspan="7" class="text-center text-danger">${data.message || 'Failed to load events'}</td></tr>`;
        }
    } catch (err) {
        console.error(err);
        if (upcomingTable) upcomingTable.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Network error occurred</td></tr>`;
        if (pastTable) pastTable.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Network error occurred</td></tr>`;
    }
}

function renderEventsTable(events) {
    const upcomingTable = document.getElementById('upcomingEventsTableBody');
    const pastTable = document.getElementById('pastEventsTableBody');
    if (upcomingTable) upcomingTable.innerHTML = '';
    if (pastTable) pastTable.innerHTML = '';

    const now = new Date();
    
    let upcomingCount = 0;
    let pastCount = 0;

    events.forEach(ev => {
        let statusBadge = '';
        if (ev.status === 'published') statusBadge = '<span class="badge-status text-bg-success"><i class="bi bi-globe me-1"></i>Published</span>';
        else if (ev.status === 'draft') statusBadge = '<span class="badge-status text-bg-secondary"><i class="bi bi-file-earmark-text me-1"></i>Draft</span>';
        else if (ev.status === 'completed') statusBadge = '<span class="badge-status text-bg-primary"><i class="bi bi-check2-all me-1"></i>Completed</span>';
        else if (ev.status === 'cancelled') statusBadge = '<span class="badge-status text-bg-danger"><i class="bi bi-x-circle me-1"></i>Cancelled</span>';
        else statusBadge = `<span class="badge-status text-bg-info">${ev.status}</span>`;

        const eventDateStr = ev.date ? new Date(ev.date).toLocaleDateString() : 'N/A';
        const eventTimeStr = ev.start_time || 'N/A';
        
        let locationStr = 'TBA';
        if (ev.location) {
            locationStr = [ev.location.venue, ev.location.address, ev.location.city, ev.location.state].filter(Boolean).join(', ') || 'TBA';
        }

        const currentVolunteers = ev.current_participants || 0;
        const maxVolunteers = ev.max_participants || 0;
        const maxStr = maxVolunteers > 0 ? maxVolunteers : '<i class="bi bi-infinity"></i>';
        const progressPct = maxVolunteers > 0 ? (currentVolunteers / maxVolunteers) * 100 : 0;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <div class="fw-bold text-dark">${ev.title || 'Untitled'}</div>
                <div class="small text-muted text-truncate" style="max-width: 200px;">${ev.description || ''}</div>
            </td>
            <td>
                <div>${eventDateStr}</div>
                <div class="small text-muted">${eventTimeStr}</div>
            </td>
            <td>
                ${ev.is_virtual ? '<span class="badge bg-light text-dark border"><i class="bi bi-laptop me-1"></i>Virtual</span>' : `<i class="bi bi-geo-alt text-muted me-1"></i>${locationStr}`}
            </td>
            <td><span class="badge bg-light text-dark border text-capitalize">${ev.category_name || 'General'}</span></td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="me-2">${currentVolunteers} / ${maxStr}</div>
                    <div class="progress" style="width: 50px; height: 6px;">
                        <div class="progress-bar bg-success" role="progressbar" style="width: ${progressPct}%"></div>
                    </div>
                </div>
            </td>
            <td>${statusBadge}</td>
            <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-warning rounded-circle me-1" title="View Feedback" onclick="viewEventFeedback('${ev.id}', '${ev.title ? ev.title.replace(/'/g, "\\'") : 'Event'}')"><i class="bi bi-star-half"></i></button>
                <button class="btn btn-sm btn-outline-primary rounded-circle me-1" title="Manage Volunteers" onclick="manageVolunteers('${ev.id}', '${ev.title ? ev.title.replace(/'/g, "\\'") : 'Event'}', '${ev.date || ''}', '${ev.start_time || ''}')"><i class="bi bi-people-fill"></i></button>
                <button class="btn btn-sm btn-outline-secondary rounded-circle me-1" title="Edit" onclick="editEvent('${ev.id}')"><i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger rounded-circle" title="Delete" onclick="deleteEvent('${ev.id}')"><i class="bi bi-trash"></i></button>
            </td>
        `;
        
        let eventDatetime = null;
        if (ev.date) {
            eventDatetime = new Date(`${ev.date}T${ev.start_time || '00:00'}:00`);
        }
        
        if (ev.status === 'completed' || ev.status === 'cancelled' || (eventDatetime && eventDatetime < now)) {
            if (pastTable) pastTable.appendChild(tr);
            pastCount++;
        } else {
            if (upcomingTable) upcomingTable.appendChild(tr);
            upcomingCount++;
        }
    });

    if (upcomingCount === 0 && upcomingTable) {
        upcomingTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No upcoming events found. Click Create Event to get started.</td></tr>';
    }
    if (pastCount === 0 && pastTable) {
        pastTable.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No past events found.</td></tr>';
    }
}

// ==========================================
// Event Specific Volunteer Management
// ==========================================
let currentManageEventId = null;
let manageEventVolunteersModal = null;
let awardHoursModal = null;
let rejectModal = null;
let selectedRequestId = null;

let currentManageEventDatetime = null;

async function manageVolunteers(eventId, eventTitle, eventDate, eventTime) {
    currentManageEventId = eventId;
    if (eventDate) {
        currentManageEventDatetime = new Date(`${eventDate}T${eventTime || '00:00'}:00`);
    } else {
        currentManageEventDatetime = null;
    }
    document.getElementById('manageEventTitle').innerText = eventTitle;
    
    if (!manageEventVolunteersModal) {
        manageEventVolunteersModal = new bootstrap.Modal(document.getElementById('manageEventVolunteersModal'));
    }
    if (!awardHoursModal) {
        awardHoursModal = new bootstrap.Modal(document.getElementById('awardHoursModal'));
    }
    if (!rejectModal) {
        rejectModal = new bootstrap.Modal(document.getElementById('rejectModal'));
    }
    
    manageEventVolunteersModal.show();
    await fetchEventVolunteers(eventId);
}

async function fetchEventVolunteers(eventId) {
    const tbody = document.getElementById('eventVolunteersTableBody');
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4"><div class="spinner-border text-primary spinner-border-sm"></div> Loading...</td></tr>`;
    
    try {
        const response = await fetch(`/api/admin/events/${eventId}/requests`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}` }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            renderEventVolunteers(data.data);
        } else {
            throw new Error(data.message || 'Error fetching volunteers');
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Failed to load volunteers.</td></tr>`;
    }
}

function renderEventVolunteers(requests) {
    const tbody = document.getElementById('eventVolunteersTableBody');
    tbody.innerHTML = '';
    
    if (requests.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No volunteers found for this event.</td></tr>`;
        return;
    }
    
    const now = new Date();
    const isPastEvent = !currentManageEventDatetime || currentManageEventDatetime <= now;
    
    requests.forEach(req => {
        const tr = document.createElement('tr');
        
        let statusClass = 'bg-warning text-dark';
        if (req.status === 'approved') statusClass = 'bg-primary text-white';
        else if (req.status === 'rejected') statusClass = 'bg-danger text-white';
        else if (req.status === 'attended') statusClass = 'bg-success text-white';
        
        const volName = req.user?.name || req.volunteer_name || 'N/A';
        const volEmail = req.user?.email || req.volunteer_email || 'N/A';
        
        tr.innerHTML = `
            <td>
                <div class="fw-bold">${volName}</div>
                <div class="small text-muted">${req.remarks || ''}</div>
            </td>
            <td>${volEmail}</td>
            <td>${new Date(req.created_at || req.applied_date).toLocaleDateString()}</td>
            <td><span class="badge ${statusClass}">${(req.status || 'pending').toUpperCase()}</span></td>
            <td class="text-end text-nowrap">
                ${req.status === 'pending' ? `
                    <button class="btn btn-sm btn-outline-success rounded-circle me-1" onclick="approveRequest('${req.id || req._id}')" title="Approve"><i class="bi bi-check-lg"></i></button>
                    <button class="btn btn-sm btn-outline-danger rounded-circle" onclick="openRejectModal('${req.id || req._id}')" title="Reject"><i class="bi bi-x-lg"></i></button>
                ` : req.status === 'approved' ? `
                    ${isPastEvent ? `<button class="btn btn-sm btn-outline-primary rounded-pill" onclick="openAwardModal('${req.id || req._id}')" title="Award Hours & Mark Attended"><i class="bi bi-award me-1"></i> Award Hours</button>` : `<span class="small text-muted fst-italic">Awaiting event...</span>`}
                ` : `
                    <button class="btn btn-sm btn-outline-secondary rounded-pill" disabled>${req.status === 'attended' ? 'Attended' : 'Processed'}</button>
                `}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================
// Event Feedback Logic
// ==========================================
let feedbackModalInstance = null;

async function viewEventFeedback(eventId, eventTitle) {
    document.getElementById('feedbackModalEventTitle').innerText = eventTitle;
    const body = document.getElementById('eventFeedbackBody');
    body.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-warning spinner-border-sm"></div> Loading feedback...</div>';
    
    if (!feedbackModalInstance) {
        feedbackModalInstance = new bootstrap.Modal(document.getElementById('adminFeedbackModal'));
    }
    feedbackModalInstance.show();
    
    try {
        const response = await fetch(`/api/events/${eventId}/feedback`, {
            headers: { 'Authorization': `Bearer ${getAuthToken()}` }
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            renderFeedbackData(data.data);
        } else {
            body.innerHTML = `<div class="text-danger text-center py-4">${data.message || 'Error fetching feedback'}</div>`;
        }
    } catch (err) {
        body.innerHTML = `<div class="text-danger text-center py-4">Network error fetching feedback</div>`;
    }
}

function renderFeedbackData(data) {
    const body = document.getElementById('eventFeedbackBody');
    if (!data.feedbacks || data.feedbacks.length === 0) {
        body.innerHTML = '<div class="text-muted text-center py-4">No feedback has been submitted for this event yet.</div>';
        return;
    }
    
    let html = `
        <div class="text-center mb-4">
            <h1 class="display-4 fw-bold text-warning mb-0">${data.average_rating}</h1>
            <div class="fs-4 text-warning">
                ${'<i class="bi bi-star-fill"></i>'.repeat(Math.round(data.average_rating))}${'<i class="bi bi-star"></i>'.repeat(5 - Math.round(data.average_rating))}
            </div>
            <p class="text-muted">Based on ${data.total_reviews} reviews</p>
        </div>
        <div class="list-group list-group-flush">
    `;
    
    data.feedbacks.forEach(f => {
        const dateStr = f.date ? new Date(f.date).toLocaleDateString() : 'Unknown Date';
        html += `
            <div class="list-group-item px-0 py-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-warning text-dark"><i class="bi bi-star-fill me-1"></i>${f.rating}</span>
                    <span class="text-muted small">${dateStr}</span>
                </div>
                <p class="mb-0 text-dark" style="white-space: pre-line;">${f.feedback ? f.feedback : '<em class="text-muted">No comment provided.</em>'}</p>
            </div>
        `;
    });
    
    html += '</div>';
    body.innerHTML = html;
}

async function approveRequest(reqId) {
    try {
        const response = await fetch(`/api/admin/requests/${reqId}/approve`, { 
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ remarks: 'Approved' })
        });
        
        if (response.ok) {
            if(window.showToast) showToast('Success', 'Request approved!', 'success');
            fetchEventVolunteers(currentManageEventId);
        } else {
            const data = await response.json();
            if(window.showToast) showToast('Error', data.message || 'Failed to approve', 'danger');
        }
    } catch(err) {
        if(window.showToast) showToast('Error', 'Network error', 'danger');
    }
}

function openRejectModal(reqId) {
    selectedRequestId = reqId;
    document.getElementById('rejectRemarks').value = '';
    rejectModal.show();
}

function openAwardModal(reqId) {
    selectedRequestId = reqId;
    document.getElementById('awardHoursInput').value = '';
    awardHoursModal.show();
}

// Bind modal confirm buttons
document.addEventListener('DOMContentLoaded', () => {
    const confirmRejectBtn = document.getElementById('confirmRejectBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', async () => {
            const remarks = document.getElementById('rejectRemarks').value;
            if (remarks.length < 3) return alert("Please provide a reason.");
            
            const orig = confirmRejectBtn.innerHTML;
            confirmRejectBtn.innerHTML = '...';
            confirmRejectBtn.disabled = true;
            
            try {
                const res = await fetch(`/api/admin/requests/${selectedRequestId}/reject`, { 
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ remarks })
                });
                if (res.ok) {
                    rejectModal.hide();
                    fetchEventVolunteers(currentManageEventId);
                } else {
                    alert("Error rejecting request.");
                }
            } catch(e) {} finally {
                confirmRejectBtn.innerHTML = orig;
                confirmRejectBtn.disabled = false;
            }
        });
    }

    const confirmAwardBtn = document.getElementById('confirmAwardBtn');
    if (confirmAwardBtn) {
        confirmAwardBtn.addEventListener('click', async () => {
            const hours = document.getElementById('awardHoursInput').value;
            if (!hours || isNaN(hours) || hours <= 0) return alert("Please enter valid hours.");
            
            const orig = confirmAwardBtn.innerHTML;
            confirmAwardBtn.innerHTML = '...';
            confirmAwardBtn.disabled = true;
            
            try {
                const res = await fetch(`/api/admin/requests/${selectedRequestId}/attended`, { 
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('admin_access_token') || ''}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hours })
                });
                if (res.ok) {
                    awardHoursModal.hide();
                    fetchEventVolunteers(currentManageEventId);
                    if(window.showToast) showToast('Success', 'Hours awarded and certificate generated!', 'success');
                } else {
                    const data = await res.json();
                    alert("Error: " + data.message);
                }
            } catch(e) {} finally {
                confirmAwardBtn.innerHTML = orig;
                confirmAwardBtn.disabled = false;
            }
        });
    }
});

function resetCreateForm() {
    editingEventId = null;
    document.getElementById('createEventModalLabel').innerHTML = '<i class="bi bi-calendar-plus-fill me-2"></i> Create New Event';
    document.getElementById('btnSubmitEvent').innerHTML = '<i class="bi bi-check2-circle me-1"></i> Create Event';
    document.getElementById('createEventForm').reset();
    
    document.getElementById('evIsVirtual').checked = false;
    document.getElementById('evIsVirtual').dispatchEvent(new Event('change'));
    
    document.getElementById('evStartDate')._flatpickr.clear();
    document.getElementById('evEndDate')._flatpickr.clear();
}

function editEvent(id) {
    editingEventId = id;
    const ev = currentEvents.find(e => e.id === id);
    if (!ev) return;
    
    document.getElementById('createEventModalLabel').innerHTML = '<i class="bi bi-pencil-fill me-2"></i> Edit Event';
    document.getElementById('btnSubmitEvent').innerHTML = '<i class="bi bi-check2-circle me-1"></i> Save Changes';
    
    document.getElementById('evTitle').value = ev.title || '';
    document.getElementById('evDescription').value = ev.description || '';
    
    // Attempt to match category_id or fallback to a default value if category mapping is complex.
    // Assuming backend returns category_id. The form uses strings like "environment".
    // For now we'll just leave it or try to map.
    
    document.getElementById('evMaxVolunteers').value = ev.max_participants || 0;
    document.getElementById('evSkills').value = (ev.tags || []).join(', ');
    
    // Location / Virtual
    document.getElementById('evIsVirtual').checked = !!ev.is_virtual;
    document.getElementById('evIsVirtual').dispatchEvent(new Event('change'));
    
    if (ev.is_virtual) {
        document.getElementById('evMeetingLink').value = (ev.location && ev.location.map_link) ? ev.location.map_link : '';
    } else {
        document.getElementById('evLocation').value = (ev.location && ev.location.venue) ? ev.location.venue : '';
        document.getElementById('evAddress').value = (ev.location && ev.location.address) ? ev.location.address : '';
    }
    
    // Status
    if (ev.status === 'published') {
        document.getElementById('statusPublished').checked = true;
    } else {
        document.getElementById('statusDraft').checked = true;
    }
    
    // Dates
    if (ev.date) {
        const startDateTime = ev.start_time ? `${ev.date}T${ev.start_time}` : ev.date;
        document.getElementById('evStartDate')._flatpickr.setDate(startDateTime);
    }
    if (ev.end_time) {
        // We only have date and end_time, so we assume end date is same as start date
        const endDateTime = `${ev.date}T${ev.end_time}`;
        document.getElementById('evEndDate')._flatpickr.setDate(endDateTime);
    }
    
    const modal = new bootstrap.Modal(document.getElementById('createEventModal'));
    modal.show();
}

async function handleCreateEvent() {
    const form = document.getElementById('createEventForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const payload = {
        title: document.getElementById('evTitle').value,
        description: document.getElementById('evDescription').value,
        category: document.getElementById('evCategory').value,
        start_date: document.getElementById('evStartDate').value,
        is_virtual: document.getElementById('evIsVirtual').checked,
        max_volunteers: parseInt(document.getElementById('evMaxVolunteers').value, 10),
        status: document.getElementById('statusPublished').checked ? 'published' : 'draft',
    };

    const endDate = document.getElementById('evEndDate').value;
    if (endDate) payload.end_date = endDate;

    if (payload.is_virtual) {
        payload.meeting_link = document.getElementById('evMeetingLink').value;
    } else {
        payload.location = document.getElementById('evLocation').value;
        payload.address = document.getElementById('evAddress').value;
    }

    const skillsRaw = document.getElementById('evSkills').value;
    if (skillsRaw) {
        payload.skills_required = skillsRaw.split(',').map(s => s.trim()).filter(s => s);
    }

    const btn = document.getElementById('btnSubmitEvent');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    btn.disabled = true;

    try {
        const method = editingEventId ? 'PUT' : 'POST';
        const url = editingEventId ? `/api/events/${editingEventId}` : '/api/events/';
        
        const res = await fetch(url, {
            method: method,
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        if (data.status === 'success') {
            const modalEl = document.getElementById('createEventModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            fetchEvents(1);
        } else {
            if (window.showToast) window.showToast('Error', data.message || `Failed to ${editingEventId ? 'update' : 'create'} event`, 'danger');
            else alert(data.message || `Failed to ${editingEventId ? 'update' : 'create'} event`);
        }
    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast('Error', 'Network error while saving event', 'danger');
        else alert('Network error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function deleteEvent(eventId) {
    if (!confirm('Are you sure you want to delete this event? This action cannot be undone.')) return;

    try {
        const token = getAuthToken();
        const res = await fetch(`/api/events/${eventId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            if (window.showToast) window.showToast('Success', 'Event deleted.', 'success');
            fetchEvents();
        } else {
            if (window.showToast) window.showToast('Error', data.message || 'Failed to delete', 'danger');
            else alert(data.message);
        }
    } catch (err) {
        console.error(err);
        alert('Error deleting event.');
    }
}
