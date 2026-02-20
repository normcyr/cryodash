/**
 * Authentication utilities for CryoDash
 * Handles JWT tokens, authorization, and session management
 */

const API_URL = '/api';

/**
 * Check if user is authenticated
 * @returns {boolean} True if access token exists
 */
function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

/**
 * Check if current user is admin
 * @returns {boolean} True if user has admin privileges
 */
function isAdmin() {
    return localStorage.getItem('is_admin') === 'true';
}

/**
 * Get current user info
 * @returns {Object} User info with username and is_admin
 */
function getCurrentUser() {
    return {
        username: localStorage.getItem('username'),
        is_admin: isAdmin(),
    };
}

/**
 * Get the current access token
 * @returns {string|null} JWT access token or null
 */
function getAccessToken() {
    return localStorage.getItem('access_token');
}

/**
 * Set authentication token and user info
 * @param {string} token - JWT access token
 * @param {string} username - Username
 * @param {boolean} isAdmin - Admin status
 */
function setAuthToken(token, username, isAdmin) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('username', username);
    localStorage.setItem('is_admin', isAdmin);
}

/**
 * Clear authentication (logout)
 */
function clearAuthToken() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    localStorage.removeItem('is_admin');
}

/**
 * Make an authenticated API request
 * @param {string} endpoint - API endpoint path (e.g., '/instruments')
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function authenticatedFetch(endpoint, options = {}) {
    const token = getAccessToken();
    const headers = options.headers || {};

    // Add JWT token if available
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });

    // If 401, token expired - redirect to login
    if (response.status === 401) {
        clearAuthToken();
        window.location.href = '/login.html';
        return response;
    }

    return response;
}

/**
 * Verify current session is valid
 * @returns {Promise<boolean>} True if session is valid
 */
async function verifySession() {
    if (!isAuthenticated()) {
        return false;
    }

    try {
        const response = await authenticatedFetch('/auth/me');
        if (response.ok) {
            const data = await response.json();
            setAuthToken(
                getAccessToken(),
                data.username,
                data.is_admin
            );
            return true;
        }
        return false;
    } catch (error) {
        console.error('Session verification failed:', error);
        return false;
    }
}

/**
 * Logout user
 */
async function logout() {
    try {
        await authenticatedFetch('/auth/logout', { method: 'POST' });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        clearAuthToken();
        window.location.href = '/login.html';
    }
}

/**
 * Protect page - redirect to login if not authenticated
 * @param {boolean} requireAdmin - If true, redirect unless user is admin
 */
async function protectPage(requireAdmin = false) {
    const isValid = await verifySession();

    if (!isValid) {
        window.location.href = '/login.html';
        return false;
    }

    if (requireAdmin && !isAdmin()) {
        window.location.href = '/';
        return false;
    }

    return true;
}

/**
 * Add auth UI controls to page
 * Shows username and logout button in a header or sidebar
 */
function setupAuthUI() {
    const user = getCurrentUser();

    if (!isAuthenticated()) {
        return;
    }

    // Create auth UI element
    const authUI = document.createElement('div');
    authUI.className = 'auth-ui';
    authUI.innerHTML = `
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span style="color: #cbd5e1;">
                👤 ${user.username}${user.is_admin ? ' (Admin)' : ''}
            </span>
            <button id="logout-btn" class="logout-button" style="
                padding: 0.5rem 1rem;
                background: #ef4444;
                color: #fff;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.875rem;
            ">
                Logout
            </button>
        </div>
    `;

    // Add to page
    const navbar = document.querySelector('.navbar') || document.querySelector('nav');
    if (navbar) {
        navbar.appendChild(authUI);
    }

    // Setup logout click handler
    document.getElementById('logout-btn')?.addEventListener('click', logout);
}

/**
 * Hide admin-only sections if not admin
 */
function hideAdminSections() {
    if (!isAdmin()) {
        document.querySelectorAll('[data-admin-only]').forEach(el => {
            el.style.display = 'none';
        });
    }
}
