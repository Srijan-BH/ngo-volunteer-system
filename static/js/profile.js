/**
 * Profile Page Logic
 * Handles image preview, tag inputs, and form submissions.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ==========================================
    // Fetch Profile Data on Load
    // ==========================================
    async function fetchProfileData() {
        try {
            const res = await (window.api ? window.api.get('/auth/me') : fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` }
            }).then(r => r.json()));
            
            const data = window.api ? res.data : res;
            if (data.status === 'success' && data.data) {
                const user = data.data.user || data.data;
                
                // Populate Header
                document.getElementById('profileHeaderName').textContent = user.full_name || 'Volunteer';
                if (user.created_at) {
                    const date = new Date(user.created_at);
                    document.getElementById('profileHeaderDate').textContent = `Volunteer since ${date.toLocaleString('default', { month: 'short' })} ${date.getFullYear()}`;
                }
                
                if (user.avatar_url) {
                    document.getElementById('profileAvatar').src = user.avatar_url;
                } else {
                    document.getElementById('profileAvatar').src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.full_name || 'V')}&background=random`;
                }

                // Populate Form Fields
                if (document.getElementById('fullName')) document.getElementById('fullName').value = user.full_name || '';
                if (document.getElementById('profileName')) document.getElementById('profileName').value = user.full_name || ''; // handle both IDs just in case
                if (document.getElementById('emailAddress')) document.getElementById('emailAddress').value = user.email || '';
                if (document.getElementById('mobileNumber')) document.getElementById('mobileNumber').value = user.mobile || '';
                if (document.getElementById('profileMobile')) document.getElementById('profileMobile').value = user.mobile || '';
                if (document.getElementById('city')) document.getElementById('city').value = (user.address && user.address.city) ? user.address.city : (user.city || '');
                
                // Populate Tags
                if (document.getElementById('skillsData') && user.skills) {
                    document.getElementById('skillsData').value = user.skills.join(',');
                } else if (document.getElementById('skillsData')) {
                    document.getElementById('skillsData').value = '';
                }
                
                if (document.getElementById('interestsData') && user.interests) {
                    document.getElementById('interestsData').value = user.interests.join(',');
                } else if (document.getElementById('interestsData')) {
                    document.getElementById('interestsData').value = '';
                }

                // Re-initialize tags if the function exists
                if (typeof renderTagsSkills === 'function') renderTagsSkills();
                if (typeof renderTagsInterests === 'function') renderTagsInterests();
            }
        } catch (err) {
            console.error('Failed to fetch profile data', err);
        }
    }

    async function fetchVolunteerHistory() {
        try {
            const token = localStorage.getItem('access_token') || '';
            if (!token) return;

            const res = await fetch('/api/dashboard/volunteer', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            
            if (data.status === 'success') {
                const stats = data.data.stats || {};
                document.getElementById('histStatEvents').textContent = stats.joined_events || 0;
                document.getElementById('histStatHours').textContent = `${stats.hours_logged || 0}h`;

                const history = data.data.history || [];
                const timeline = document.getElementById('volunteerHistoryTimeline');
                
                if (history.length === 0) {
                    timeline.innerHTML = '<div class="text-center text-muted py-3">No volunteer history yet.</div>';
                    return;
                }
                
                timeline.innerHTML = '';
                history.forEach(item => {
                    const dateStr = item.start_date ? new Date(item.start_date).toLocaleDateString(undefined, {year: 'numeric', month: 'long', day: 'numeric'}) : 'N/A';
                    let locationStr = 'TBA';
                    if (item.location) {
                        locationStr = [item.location.venue, item.location.city].filter(Boolean).join(', ') || 'TBA';
                    }
                    
                    timeline.innerHTML += `
                        <div class="timeline-item">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <div class="timeline-date">${dateStr}</div>
                                <div class="timeline-title">${item.title}</div>
                                <div class="timeline-meta">
                                    <span><i class="bi bi-geo-alt me-1"></i> ${locationStr}</span>
                                    <span><i class="bi bi-stopwatch me-1"></i> ${item.hours_logged || 0} hrs</span>
                                </div>
                            </div>
                        </div>
                    `;
                });
            }
        } catch (err) {
            console.error('Failed to fetch volunteer history', err);
            document.getElementById('volunteerHistoryTimeline').innerHTML = '<div class="text-center text-danger py-3">Failed to load history.</div>';
        }
    }

    // Call fetch on load
    fetchProfileData();
    fetchVolunteerHistory();

    // ==========================================
    // Image Upload & Preview
    // ==========================================
    const avatarInput = document.getElementById('avatarInput');
    const profileAvatar = document.getElementById('profileAvatar');

    if (avatarInput && profileAvatar) {
        avatarInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                // Simple validation
                if (!file.type.startsWith('image/')) {
                    if (window.showToast) showToast('Error', 'Please upload a valid image file.', 'danger');
                    return;
                }
                if (file.size > 2 * 1024 * 1024) {
                    if (window.showToast) showToast('Error', 'Image must be less than 2MB.', 'danger');
                    return;
                }

                // Show preview immediately
                const reader = new FileReader();
                reader.onload = (e) => {
                    profileAvatar.src = e.target.result;
                };
                reader.readAsDataURL(file);
                
                // Upload to backend
                const formData = new FormData();
                formData.append('avatar', file);
                
                try {
                    const res = await fetch('/api/auth/me/avatar', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}` },
                        body: formData
                    });
                    
                    const data = await res.json();
                    if (data.status === 'success') {
                        if (window.showToast) showToast('Success', 'Profile image updated successfully.', 'success');
                    } else {
                        if (window.showToast) showToast('Error', data.message || 'Failed to upload image.', 'danger');
                    }
                } catch (err) {
                    if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
                }
            }
        });
    }

    // ==========================================
    // Tags Input (Skills & Interests)
    // ==========================================
    function setupTagInput(containerId, hiddenInputId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const input = container.querySelector('.tag-input');
        const hiddenInput = document.getElementById(hiddenInputId);
        
        // Initial tags from hidden input (if any)
        let tags = hiddenInput.value ? hiddenInput.value.split(',').map(t => t.trim()).filter(Boolean) : [];

        function renderTags() {
            // Remove existing tags in DOM
            container.querySelectorAll('.skill-tag').forEach(el => el.remove());
            
            // Re-render
            tags.forEach((tag, index) => {
                const tagEl = document.createElement('span');
                tagEl.className = 'skill-tag';
                tagEl.innerHTML = `${tag} <i class="bi bi-x-circle remove-tag" data-index="${index}"></i>`;
                container.insertBefore(tagEl, input);
            });
            
            // Update hidden input
            hiddenInput.value = tags.join(',');
        }

        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-tag')) {
                const index = parseInt(e.target.getAttribute('data-index'));
                tags.splice(index, 1);
                renderTags();
            } else {
                input.focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const val = input.value.trim().replace(',', '');
                if (val && !tags.includes(val)) {
                    tags.push(val);
                    input.value = '';
                    renderTags();
                }
            } else if (e.key === 'Backspace' && input.value === '' && tags.length > 0) {
                tags.pop();
                renderTags();
            }
        });
        
        // Expose render function for the fetch loader to call later
        if (containerId === 'skillsContainer') window.renderTagsSkills = renderTags;
        if (containerId === 'interestsContainer') window.renderTagsInterests = renderTags;
        
        // Initial render
        renderTags();
    }

    setupTagInput('skillsContainer', 'skillsData');
    setupTagInput('interestsContainer', 'interestsData');

    // ==========================================
    // Form Submissions
    // ==========================================
    
    // Personal Details Form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = profileForm.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            btn.disabled = true;
            const fullName = document.getElementById('fullName')?.value.trim() || document.getElementById('profileName')?.value.trim();
            const mobile = document.getElementById('mobileNumber')?.value.trim() || document.getElementById('profileMobile')?.value.trim();
            const city = document.getElementById('city')?.value.trim() || '';
            const skills = document.getElementById('skillsData')?.value.split(',').filter(Boolean) || [];
            const interests = document.getElementById('interestsData')?.value.split(',').filter(Boolean) || [];

            try {
                const payload = {
                    full_name: fullName,
                    mobile: mobile,
                    location: city,
                    skills: skills,
                    interests: interests
                };
                
                const res = await (window.api ? window.api.put('/auth/me', payload) : fetch('/api/auth/me', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                    },
                    body: JSON.stringify(payload)
                }).then(r => r.json()));
                
                const data = window.api ? res.data : res;
                
                if (data.status === 'success') {
                    if (window.showToast) showToast('Success', 'Profile details updated successfully!', 'success');
                } else {
                    if (window.showToast) showToast('Error', data.message || 'Update failed.', 'danger');
                }
            } catch (error) {
                if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }

    // Password Form
    const passwordForm = document.getElementById('passwordForm');
    if (passwordForm) {
        passwordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const currentPass = document.getElementById('currentPassword').value;
            const newPass = document.getElementById('newPassword').value;
            const confirmPass = document.getElementById('confirmNewPassword').value;

            if (newPass !== confirmPass) {
                if (window.showToast) showToast('Error', 'New passwords do not match.', 'danger');
                return;
            }

            if (newPass.length < 8) {
                if (window.showToast) showToast('Error', 'Password must be at least 8 characters long.', 'danger');
                return;
            }

            const btn = passwordForm.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
            btn.disabled = true;

            try {
                const res = await (window.api ? window.api.put('/auth/change-password', {
                    current_password: currentPass,
                    new_password: newPass,
                    confirm_password: confirmPass
                }) : fetch('/api/auth/change-password', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
                    },
                    body: JSON.stringify({
                        current_password: currentPass,
                        new_password: newPass,
                        confirm_password: confirmPass
                    })
                }).then(r => r.json()));
                
                const data = window.api ? res.data : res;
                
                if (data.status === 'success') {
                    passwordForm.reset();
                    if (window.showToast) showToast('Success', 'Password changed successfully!', 'success');
                } else {
                    if (window.showToast) showToast('Error', data.message || 'Failed to change password.', 'danger');
                }
            } catch (error) {
                if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }

    // ==========================================
    // Global Toast Notification Helper
    // ==========================================
    function showToast(title, message, type='primary') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;

        const toastId = 'toast-' + Date.now();
        
        let icon = 'bi-info-circle';
        if(type === 'success') icon = 'bi-check-circle';
        if(type === 'danger') icon = 'bi-exclamation-triangle';
        if(type === 'warning') icon = 'bi-exclamation-circle';

        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0 animate-fade-in-up" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi ${icon} me-2"></i>
                        <strong>${title}</strong>
                        <div class="mt-1 small">${message}</div>
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastEl = document.getElementById(toastId);
        const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
        bsToast.show();
        
        // Remove from DOM after hidden
        toastEl.addEventListener('hidden.bs.toast', () => {
            toastEl.remove();
        });
    }
});
