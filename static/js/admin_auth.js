/**
 * Admin Authentication Script
 * Handles login form submission and JWT storage.
 */
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('adminLoginForm');
    const alertBox = document.getElementById('adminLoginAlert');
    const btn = document.getElementById('loginBtn');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const rememberMe = document.getElementById('rememberMe').checked;

            // Reset UI
            alertBox.classList.add('d-none');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Authenticating...';

            try {
                const response = await fetch('/api/admin/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, remember_me: rememberMe })
                });

                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    // Save tokens
                    localStorage.setItem('admin_access_token', data.data.access_token);
                    localStorage.setItem('admin_refresh_token', data.data.refresh_token);
                    localStorage.setItem('admin_user', JSON.stringify(data.data.entity));

                    btn.innerHTML = '<i class="bi bi-check-circle me-2"></i> Success!';
                    btn.classList.replace('btn-admin', 'btn-success');
                    
                    // Redirect to Admin Dashboard
                    setTimeout(() => {
                        window.location.href = '/admin/dashboard';
                    }, 500);
                } else {
                    alertBox.textContent = data.message || "Invalid credentials. Please try again.";
                    alertBox.classList.remove('d-none');
                    btn.disabled = false;
                    btn.textContent = 'Sign In';
                }
            } catch (error) {
                console.error("Login error:", error);
                alertBox.textContent = "Could not connect to the server. Please try again later.";
                alertBox.classList.remove('d-none');
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        });
    }
});
