/**
 * Auth Pages — Client-Side Validation & Interactivity
 * Handles: password strength, show/hide, real-time validation, form submission
 */

document.addEventListener('DOMContentLoaded', () => {
    initPasswordToggles();
    initPasswordStrength();
    initSignupValidation();
    initLoginValidation();
    initForgotPasswordValidation();
    initSocialLogins();
});

/* =========================================================================
   Social Logins (Mock)
   ========================================================================= */
function initSocialLogins() {
    document.querySelectorAll('.social-login-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const provider = this.textContent.trim();
            if (window.showToast) {
                showToast('Demo Environment', `${provider} login is not configured in this demo version. Please use email and password.`, 'warning');
            } else {
                alert(`${provider} login is not configured in this demo version.`);
            }
        });
    });
}

/* =========================================================================
   Show / Hide Password
   ========================================================================= */
function initPasswordToggles() {
    document.querySelectorAll('.password-toggle').forEach(btn => {
        btn.addEventListener('click', function () {
            const input = this.closest('.auth-input-group').querySelector('input');
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('bi-eye', 'bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('bi-eye-slash', 'bi-eye');
            }
        });
    });
}

/* =========================================================================
   Password Strength Meter
   ========================================================================= */
function initPasswordStrength() {
    const passwordInput = document.getElementById('signupPassword');
    if (!passwordInput) return;

    const meterBars = document.querySelectorAll('.strength-bar');
    const label     = document.querySelector('.strength-label');
    const reqList   = document.querySelectorAll('.password-requirements li');

    passwordInput.addEventListener('input', function () {
        const val   = this.value;
        const score = calcPasswordStrength(val);

        // Update bars
        const levels = ['weak', 'fair', 'good', 'strong', 'very-strong'];
        const levelNames = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
        const level = levels[score - 1] || '';

        meterBars.forEach((bar, i) => {
            bar.classList.remove('active', 'weak', 'fair', 'good', 'strong', 'very-strong');
            if (i < score) {
                bar.classList.add('active', level);
            }
        });

        if (label) {
            label.textContent = val ? levelNames[score - 1] || '' : '';
            label.className = 'strength-label ' + level;
        }

        // Update requirements checklist
        updateRequirements(val, reqList);

        // Validate confirm password if it has a value
        const confirmInput = document.getElementById('signupConfirmPassword');
        if (confirmInput && confirmInput.value) {
            validateConfirmPassword(confirmInput, val);
        }
    });
}

function calcPasswordStrength(password) {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8)                 score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password))                  score++;
    if (/[^a-zA-Z0-9]/.test(password))        score++;
    if (password.length >= 12)                score++;
    return Math.min(score, 5);
}

function updateRequirements(password, items) {
    const rules = [
        { test: p => p.length >= 8,           idx: 0 },
        { test: p => /[A-Z]/.test(p),         idx: 1 },
        { test: p => /[a-z]/.test(p),         idx: 2 },
        { test: p => /\d/.test(p),            idx: 3 },
        { test: p => /[^a-zA-Z0-9]/.test(p),  idx: 4 },
    ];
    rules.forEach(rule => {
        const li = items[rule.idx];
        if (!li) return;
        if (rule.test(password)) {
            li.classList.add('met');
            li.classList.remove('unmet');
        } else {
            li.classList.remove('met');
            li.classList.add('unmet');
        }
    });
}

/* =========================================================================
   Validation Helpers
   ========================================================================= */
function showFieldError(input, errorEl, message) {
    input.classList.add('is-invalid');
    input.classList.remove('is-valid');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('visible');
    }
}

function showFieldSuccess(input, errorEl) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    if (errorEl) {
        errorEl.classList.remove('visible');
    }
}

function clearField(input, errorEl) {
    input.classList.remove('is-invalid', 'is-valid');
    if (errorEl) errorEl.classList.remove('visible');
}

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function validateMobile(mobile) {
    const cleaned = mobile.replace(/[\s\-()]/g, '');
    return /^(?:\+?91|0)?[6-9]\d{9}$/.test(cleaned) || /^\+?[1-9]\d{6,14}$/.test(cleaned);
}

function validateConfirmPassword(confirmInput, password) {
    const errorEl = confirmInput.closest('.auth-input-group').querySelector('.field-error');
    if (!confirmInput.value) {
        clearField(confirmInput, errorEl);
        return false;
    }
    if (confirmInput.value !== password) {
        showFieldError(confirmInput, errorEl, 'Passwords do not match.');
        return false;
    }
    showFieldSuccess(confirmInput, errorEl);
    return true;
}

function setButtonLoading(btn, loading) {
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

/* =========================================================================
   Signup Form Validation
   ========================================================================= */
function initSignupValidation() {
    const form = document.getElementById('signupForm');
    if (!form) return;

    const fields = {
        name:     { input: document.getElementById('signupName'),     error: null },
        email:    { input: document.getElementById('signupEmail'),    error: null },
        mobile:   { input: document.getElementById('signupMobile'),   error: null },
        password: { input: document.getElementById('signupPassword'), error: null },
        confirm:  { input: document.getElementById('signupConfirmPassword'), error: null },
    };

    // Attach error elements
    Object.keys(fields).forEach(key => {
        const group = fields[key].input?.closest('.auth-input-group');
        if (group) fields[key].error = group.querySelector('.field-error');
    });

    // Real-time: Name
    fields.name.input?.addEventListener('blur', function () {
        const val = this.value.trim();
        if (!val) showFieldError(this, fields.name.error, 'Full name is required.');
        else if (val.length < 2) showFieldError(this, fields.name.error, 'Name must be at least 2 characters.');
        else if (!/^[A-Za-z][A-Za-z\s'\-.]{1,99}$/.test(val)) showFieldError(this, fields.name.error, 'Name can only contain letters, spaces, and hyphens.');
        else showFieldSuccess(this, fields.name.error);
    });

    // Real-time: Email
    fields.email.input?.addEventListener('blur', function () {
        const val = this.value.trim();
        if (!val) showFieldError(this, fields.email.error, 'Email is required.');
        else if (!validateEmail(val)) showFieldError(this, fields.email.error, 'Please enter a valid email address.');
        else showFieldSuccess(this, fields.email.error);
    });

    // Real-time: Mobile
    fields.mobile.input?.addEventListener('blur', function () {
        const val = this.value.trim();
        if (!val) showFieldError(this, fields.mobile.error, 'Mobile number is required.');
        else if (!validateMobile(val)) showFieldError(this, fields.mobile.error, 'Enter a valid 10-digit mobile number.');
        else showFieldSuccess(this, fields.mobile.error);
    });

    // Real-time: Confirm Password
    fields.confirm.input?.addEventListener('input', function () {
        validateConfirmPassword(this, fields.password.input.value);
    });

    // Form submit
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        let valid = true;

        // Name
        const name = fields.name.input.value.trim();
        if (!name || name.length < 2) {
            showFieldError(fields.name.input, fields.name.error, 'Full name is required (min 2 chars).');
            valid = false;
        }

        // Email
        const email = fields.email.input.value.trim();
        if (!email || !validateEmail(email)) {
            showFieldError(fields.email.input, fields.email.error, 'Please enter a valid email.');
            valid = false;
        }

        // Mobile
        const mobile = fields.mobile.input.value.trim();
        if (!mobile || !validateMobile(mobile)) {
            showFieldError(fields.mobile.input, fields.mobile.error, 'Please enter a valid mobile number.');
            valid = false;
        }

        // Password
        const password = fields.password.input.value;
        if (!password || calcPasswordStrength(password) < 3) {
            showFieldError(fields.password.input, fields.password.error, 'Password is too weak. Meet all the requirements below.');
            valid = false;
        }

        // Confirm
        if (!validateConfirmPassword(fields.confirm.input, password)) {
            valid = false;
        }

        if (!valid) {
            if (window.showToast) showToast('Validation Error', 'Please fix the highlighted errors.', 'danger');
            return;
        }

        // Submit to API
        const btn = form.querySelector('.auth-submit-btn');
        setButtonLoading(btn, true);

        fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name:        name,
                email:            email,
                mobile:           mobile,
                password:         password,
                confirm_password: fields.confirm.input.value,
            })
        })
        .then(res => res.json())
        .then(data => {
            setButtonLoading(btn, false);
            if (data.status === 'success') {
                if (data.data?.access_token) {
                    localStorage.setItem('access_token', data.data.access_token);
                    localStorage.setItem('refresh_token', data.data.refresh_token);
                }
                if (window.showToast) showToast('Welcome! 🎉', data.message || 'Account created.', 'success');
                setTimeout(() => window.location.href = '/dashboard', 1500);
            } else {
                const msg = data.message || 'Registration failed.';
                if (window.showToast) showToast('Error', msg, 'danger');
                if (data.field === 'email')  showFieldError(fields.email.input, fields.email.error, msg);
                if (data.field === 'mobile') showFieldError(fields.mobile.input, fields.mobile.error, msg);
            }
        })
        .catch(() => {
            setButtonLoading(btn, false);
            if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
        });
    });
}

/* =========================================================================
   Login Form Validation
   ========================================================================= */
function initLoginValidation() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    const emailInput    = document.getElementById('loginEmail');
    const passwordInput = document.getElementById('loginPassword');
    const emailError    = emailInput?.closest('.auth-input-group')?.querySelector('.field-error');
    const passwordError = passwordInput?.closest('.auth-input-group')?.querySelector('.field-error');

    emailInput?.addEventListener('blur', function () {
        if (!this.value.trim()) showFieldError(this, emailError, 'Email is required.');
        else if (!validateEmail(this.value.trim())) showFieldError(this, emailError, 'Please enter a valid email.');
        else showFieldSuccess(this, emailError);
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        let valid = true;

        const email    = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email || !validateEmail(email)) {
            showFieldError(emailInput, emailError, 'Please enter a valid email.');
            valid = false;
        }
        if (!password) {
            showFieldError(passwordInput, passwordError, 'Password is required.');
            valid = false;
        }

        if (!valid) {
            if (window.showToast) showToast('Validation Error', 'Please fill in all required fields.', 'danger');
            return;
        }

        const btn = form.querySelector('.auth-submit-btn');
        setButtonLoading(btn, true);

        const rememberMe = document.getElementById('rememberMe')?.checked || false;

        fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, remember_me: rememberMe })
        })
        .then(res => res.json())
        .then(data => {
            setButtonLoading(btn, false);
            if (data.status === 'success') {
                if (data.data?.access_token) {
                    localStorage.setItem('access_token', data.data.access_token);
                    localStorage.setItem('refresh_token', data.data.refresh_token);
                }
                if (window.showToast) showToast('Welcome back! 👋', data.message || 'Login successful.', 'success');
                setTimeout(() => window.location.href = '/dashboard', 1200);
            } else {
                if (window.showToast) showToast('Login Failed', data.message || 'Invalid credentials.', 'danger');
                showFieldError(passwordInput, passwordError, data.message || 'Invalid email or password.');
            }
        })
        .catch(() => {
            setButtonLoading(btn, false);
            if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
        });
    });
}

/* =========================================================================
   Forgot Password Form
   ========================================================================= */
function initForgotPasswordValidation() {
    const form = document.getElementById('forgotPasswordForm');
    if (!form) return;

    const emailInput = document.getElementById('forgotEmail');
    const emailError = emailInput?.closest('.auth-input-group')?.querySelector('.field-error');

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const email = emailInput.value.trim();
        if (!email || !validateEmail(email)) {
            showFieldError(emailInput, emailError, 'Please enter a valid email address.');
            if (window.showToast) showToast('Error', 'Please enter a valid email.', 'danger');
            return;
        }
        showFieldSuccess(emailInput, emailError);

        const btn = form.querySelector('.auth-submit-btn');
        setButtonLoading(btn, true);

        fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        })
        .then(res => res.json())
        .then(data => {
            setButtonLoading(btn, false);
            // Always show success (enumeration protection)
            document.getElementById('forgotFormContainer').style.display = 'none';
            document.getElementById('forgotSuccessState').classList.add('visible');
            if (window.showToast) showToast('Email Sent', data.message || 'Check your inbox.', 'success');
        })
        .catch(() => {
            setButtonLoading(btn, false);
            if (window.showToast) showToast('Network Error', 'Could not connect to the server.', 'danger');
        });
    });
}
