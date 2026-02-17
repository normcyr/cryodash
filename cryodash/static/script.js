// CryoDash Frontend Script

const API_URL = '/api';
let charts = {};  // Store multiple chart instances
// wsClients is defined in websocket-client.js
let instruments = [];  // Cache of instruments

// Initialize on page load

async function cryodashInit() {
    setupPageNavigation();
    setupAdminControls();
    setupConnectionStatusIndicator();
    setupChartControls();
    await loadInstruments();
    // Setup WebSocket connections AFTER instruments are loaded
    setupWebSocketConnections();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', cryodashInit);
} else {
    cryodashInit();
}

/**
 * Setup page navigation tabs
 */
function setupPageNavigation() {
    const navTabs = document.querySelectorAll('.nav-tab');

    navTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            const pageName = e.target.dataset.page;
            switchPage(pageName);
        });
    });
}

/**
 * Switch between pages
 */
function switchPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page-content').forEach(page => {
        page.classList.remove('active');
    });

    // Deactivate all tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected page
    document.getElementById(`${pageName}-page`).classList.add('active');

    // Activate selected tab
    document.querySelector(`[data-page="${pageName}"]`).classList.add('active');

    // If switching to charts and device is selected, load charts
    if (pageName === 'charts') {
        const device = document.getElementById('device-select').value;
        if (device) {
            loadCharts();
        }
    }

    // If switching to measurements, load measurements
    if (pageName === 'measurements') {
        loadMeasurements();
    }
}

/**
 * Fetch all instruments and display them
 */
async function loadInstruments() {
    try {
        const response = await fetch(`${API_URL}/instruments`);
        if (!response.ok) throw new Error('Failed to fetch instruments');

        instruments = await response.json();
        displayInstruments(instruments);
        populateChartSelects(instruments);
    } catch (error) {
        console.error('Error loading instruments:', error);
        showError('Erreur lors du chargement des instruments');
    }
}

/**
 * Display instruments on the grid
 */
async function displayInstruments(instruments) {
    const grid = document.getElementById('instruments-grid');

    if (instruments.length === 0) {
        grid.innerHTML = '<p class="error">Aucun instrument configuré</p>';
        return;
    }

    grid.innerHTML = '';

    for (const instrument of instruments) {
        try {
            const detailResponse = await fetch(`${API_URL}/instruments/${instrument.name}`);
            if (!detailResponse.ok) throw new Error('Failed to fetch instrument details');

            const detail = await detailResponse.json();
            const card = createInstrumentCard(detail);
            grid.appendChild(card);
        } catch (error) {
            console.error(`Error fetching details for ${instrument.name}:`, error);
        }
    }

    // Load evaporation rates for display
    await loadEvaporationRatesForDashboard();
}

/**
 * Create instrument card element
 */
function createInstrumentCard(instrument) {
    const card = document.createElement('div');
    card.className = 'instrument-card';
    card.setAttribute('data-instrument', instrument.name);

    // Add class for neo700 (dual cryogen)
    if (instrument.name === 'neo700') {
        card.classList.add('dual-cryogen-card');
    }

    // Determine overall status
    const overallStatus = determineOverallStatus(instrument.current);

    let statusClass = 'status-ok';
    if (overallStatus === 'critical') statusClass = 'status-critical';
    else if (overallStatus === 'warning') statusClass = 'status-warning';

    const headerHTML = `
        <div class="instrument-header">
            <div class="instrument-title">
                <h2>${instrument.name.toUpperCase()}</h2>
                <p class="frequency">${instrument.frequency}</p>
                ${instrument.description ? `<p class="description">${instrument.description}</p>` : ''}
            </div>
            <span class="instrument-status ${statusClass}">${overallStatus}</span>
        </div>
    `;

    const readingsHTML = `
        <div class="readings-container">
            ${instrument.current.map(reading => createReadingElement(reading)).join('')}
        </div>
    `;

    card.innerHTML = headerHTML + readingsHTML;
    return card;
}

/**
 * Create a reading element for a specific cryogen
 */
function createReadingElement(reading) {
    const timestamp = new Date(reading.timestamp);
    const year = timestamp.getFullYear();
    const month = String(timestamp.getMonth() + 1).padStart(2, '0');
    const day = String(timestamp.getDate()).padStart(2, '0');
    const hour = String(timestamp.getHours()).padStart(2, '0');
    const minute = String(timestamp.getMinutes()).padStart(2, '0');
    const formattedTime = `${year}/${month}/${day} ${hour}:${minute}`;

    return `
        <div class="cryogen-reading ${reading.status}" data-cryogen="${reading.cryogen}">
            <div class="reading-header">
                <span class="cryogen-name">${reading.cryogen}</span>
                <span class="reading-time">${formattedTime}</span>
            </div>
            <div class="level-container">
                <div class="level-value">
                    <span>Niveau</span>
                    <span>${reading.level.toFixed(1)}%</span>
                </div>
                <div class="level-bar">
                    <div class="level-fill" style="width: ${reading.level}%"></div>
                </div>
            </div>
            <div class="status-footer">
                <div class="status-indicator">
                    ${getStatusMessage(reading.status)}
                </div>
                <div class="evaporation-rate" data-evap-key="${reading.cryogen}"></div>
            </div>
        </div>
    `;
}

/**
 * Get human-readable status message
 */
function getStatusMessage(status) {
    const messages = {
        ok: '✓ Niveau normal',
        warning: '⚠ Niveau bas',
        critical: '🚨 Niveau critique',
        catastrophic: '🔥 Critique!'
    };
    return messages[status] || 'État inconnu';
}

/**
 * Determine overall status from current readings
 */
function determineOverallStatus(readings) {
    if (readings.some(r => r.status === 'critical')) return 'critical';
    if (readings.some(r => r.status === 'warning')) return 'warning';
    return 'ok';
}

/**
 * Populate select dropdowns for chart
 */
function populateChartSelects(instruments) {
    const deviceSelect = document.getElementById('device-select');

    deviceSelect.innerHTML = '<option value="">Sélectionner un appareil</option>';

    instruments.forEach(instrument => {
        const option = document.createElement('option');
        option.value = instrument.name;
        option.textContent = `${instrument.name.toUpperCase()} (${instrument.frequency})`;
        deviceSelect.appendChild(option);
    });

    deviceSelect.addEventListener('change', () => {
        // Reset charts when device changes
        destroyAllCharts();
    });
}

/**
 * Setup chart control event listeners
 */
function setupChartControls() {
    const refreshBtn = document.getElementById('refresh-chart-btn');
    refreshBtn.addEventListener('click', loadCharts);
}

/**
 * Load and display charts
 */
async function loadCharts() {
    const deviceSelect = document.getElementById('device-select');
    const hoursSelect = document.getElementById('hours-select');

    const device = deviceSelect.value;
    const hours = hoursSelect.value;

    if (!device) {
        alert('Veuillez sélectionner un appareil');
        return;
    }

    try {
        // Get instrument details to know which cryogens to display
        const response = await fetch(`${API_URL}/instruments/${device}`);
        if (!response.ok) throw new Error('Failed to fetch instrument details');

        const instrument = await response.json();
        const cryogens = instrument.cryogens.split(',').map(c => c.trim());

        // Hide both chart sections
        document.getElementById('single-chart-section').style.display = 'none';
        document.getElementById('dual-chart-section').style.display = 'none';

        if (cryogens.length === 1) {
            // Single cryogen (Neo600)
            await loadSingleChart(device, cryogens[0], hours);
        } else if (cryogens.length === 2 && device === 'neo700') {
            // Dual cryogen (Neo700)
            await loadDualCharts(device, cryogens, hours);
        }
    } catch (error) {
        console.error('Error loading charts:', error);
        showError('Erreur lors du chargement des graphiques');
    }
}

/**
 * Load single chart for one cryogen
 */
async function loadSingleChart(device, cryogen, hours) {
    try {
        // Check if Chart.js is loaded before attempting to create chart
        if (typeof Chart === 'undefined') {
            showError('Chart.js n\'a pas pu charger. Veuillez actualiser la page.');
            return;
        }

        const response = await fetch(
            `${API_URL}/instruments/${device}/history?cryogen=${cryogen}&hours=${hours}`
        );

        if (!response.ok) throw new Error('Failed to fetch history');

        const data = await response.json();

        // Show single chart section
        document.getElementById('single-chart-section').style.display = 'block';

        // Destroy previous chart if exists
        if (charts['main']) {
            charts['main'].destroy();
        }

        // Create new chart
        const ctx = document.getElementById('history-chart').getContext('2d');
        charts['main'] = createChart(ctx, data, device, cryogen);
    } catch (error) {
        console.error('Error loading single chart:', error);
        showError('Erreur lors du chargement du graphique');
    }
}

/**
 * Load dual charts for Neo700
 */
async function loadDualCharts(device, cryogens, hours) {
    try {
        // Check if Chart.js is loaded before attempting to create chart
        if (typeof Chart === 'undefined') {
            showError('Chart.js n\'a pas pu charger. Veuillez actualiser la page.');
            return;
        }

        // Fetch data for both cryogens in parallel
        const [n2Response, heResponse] = await Promise.all([
            fetch(`${API_URL}/instruments/${device}/history?cryogen=N2&hours=${hours}`),
            fetch(`${API_URL}/instruments/${device}/history?cryogen=He&hours=${hours}`)
        ]);

        if (!n2Response.ok || !heResponse.ok) {
            throw new Error('Failed to fetch history data');
        }

        const n2Data = await n2Response.json();
        const heData = await heResponse.json();

        // Show dual chart section
        document.getElementById('dual-chart-section').style.display = 'block';

        // Destroy previous charts if exist
        if (charts['n2']) charts['n2'].destroy();
        if (charts['he']) charts['he'].destroy();

        // Create charts
        const ctxN2 = document.getElementById('history-chart-n2').getContext('2d');
        const ctxHe = document.getElementById('history-chart-he').getContext('2d');

        charts['n2'] = createChart(ctxN2, n2Data, device, 'N2');
        charts['he'] = createChart(ctxHe, heData, device, 'He');
    } catch (error) {
        console.error('Error loading dual charts:', error);
        showError('Erreur lors du chargement des graphiques');
    }
}

/**
 * Create a chart instance using Chart.js
 */
function createChart(ctx, data, device, cryogen) {
    // Verify Chart.js is loaded
    if (typeof Chart === 'undefined') {
        throw new Error('Chart.js library is not loaded. Please refresh the page.');
    }

    const labels = data.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleString('fr-FR', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    });

    const levels = data.map(d => d.level);

    // Choose color based on cryogen
    const colors = {
        'N2': {
            border: '#3b82f6',
            bg: 'rgba(59, 130, 246, 0.1)'
        },
        'He': {
            border: '#ec4899',
            bg: 'rgba(236, 72, 153, 0.1)'
        }
    };

    const color = colors[cryogen] || colors['N2'];

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `Niveau de ${cryogen}`,
                data: levels,
                borderColor: color.border,
                backgroundColor: color.bg,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: color.border,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointHoverRadius: 5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#f1f5f9',
                        font: {
                            size: 12,
                            weight: '600'
                        }
                    }
                },
                title: {
                    display: true,
                    text: `Historique ${device.toUpperCase()} - ${cryogen}`,
                    color: '#f1f5f9',
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: '#cbd5e1',
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: 'rgba(51, 65, 85, 0.5)'
                    }
                },
                x: {
                    ticks: {
                        color: '#cbd5e1',
                        maxRotation: 45,
                        minRotation: 45
                    },
                    grid: {
                        color: 'rgba(51, 65, 85, 0.5)'
                    }
                }
            }
        }
    });
}

/**
 * Destroy all chart instances
 */
function destroyAllCharts() {
    Object.values(charts).forEach(chart => {
        if (chart) chart.destroy();
    });
    charts = {};
}

/**
 * Show error message
 */
function showError(message) {
    const grid = document.getElementById('instruments-grid');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    grid.innerHTML = '';
    grid.appendChild(errorDiv);
}
/**
 * Admin section functions
 */
function setupAdminControls() {
    // Manual sync button
    const syncBtn = document.getElementById('manual-sync-btn');
    if (syncBtn) {
        syncBtn.addEventListener('click', triggerManualSync);
    }

    // Log migration button
    const migrateBtn = document.getElementById('migrate-logs-btn');
    if (migrateBtn) {
        migrateBtn.addEventListener('click', triggerLogMigration);
    }

    // Evaporation rate controls
    const evapRefreshBtn = document.getElementById('evap-refresh-btn');
    if (evapRefreshBtn) {
        evapRefreshBtn.addEventListener('click', loadEvaporationRates);
    }

    // Load admin data when page is viewed
    const adminPage = document.getElementById('admin-page');
    if (adminPage) {
        // Check if admin tab is active
        const observer = new MutationObserver(() => {
            if (adminPage.classList.contains('active')) {
                loadAdminData();
                observer.disconnect();
            }
        });
        observer.observe(adminPage, { attributes: true, attributeFilter: ['class'] });
    }
}

async function loadAdminData() {
    await Promise.all([
        loadSyncStatus(),
        loadDatabaseStats(),
        loadEvaporationRates(),
        loadSyncHistory()
    ]);
}

async function loadSyncStatus() {
    try {
        const response = await fetch(`${API_URL}/sync-status`);
        const data = await response.json();
        const statusText = document.getElementById('sync-status-text');
        if (statusText) {
            statusText.innerHTML = `Statut du scheduler: <strong>${data.status}</strong><br/>Intervalle: ${data.schedule}`;
        }
    } catch (error) {
        console.error('Error loading sync status:', error);
    }
}

async function triggerManualSync() {
    const btn = document.getElementById('manual-sync-btn');
    const resultDiv = document.getElementById('sync-result');

    btn.disabled = true;
    btn.textContent = 'Synchronisation en cours...';

    try {
        const response = await fetch(`${API_URL}/sync-logs`, { method: 'POST' });
        const data = await response.json();

        resultDiv.style.display = 'block';
        if (response.ok) {
            resultDiv.className = 'sync-result success';
            resultDiv.innerHTML = `
                <strong>✓ Synchronisation réussie</strong><br/>
                <small>${data.timestamp}</small><br/>
                <ul>
                    <li>Lectures importées: ${data.total_imported}</li>
                    <li>Fichiers traités: ${data.files_processed}</li>
                    <li>Fichiers échoués: ${data.files_failed}</li>
                </ul>
            `;
        } else if (response.status === 429) {
            // Rate limited
            resultDiv.className = 'sync-result error';
            resultDiv.textContent = `⏱️ ${data.detail}`;
        } else {
            resultDiv.className = 'sync-result error';
            resultDiv.textContent = `Erreur: ${data.detail}`;
        }
    } catch (error) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'sync-result error';
        resultDiv.textContent = `Erreur: ${error.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Synchroniser maintenant';
        // Reload other admin data
        setTimeout(() => {
            loadDatabaseStats();
            loadSyncHistory();
        }, 1000);
    }
}

async function triggerLogMigration() {
    const btn = document.getElementById('migrate-logs-btn');
    const resultDiv = document.getElementById('migration-result');

    // Prompt for API key if not already stored
    let apiKey = localStorage.getItem('apiKey');
    if (!apiKey) {
        apiKey = prompt('Entrez votre clé API (API_KEY du .env):');
        if (!apiKey) {
            resultDiv.style.display = 'block';
            resultDiv.className = 'migration-result error';
            resultDiv.textContent = '❌ Migration annulée: clé API requise';
            return;
        }
        // Optionally save it for future use
        const saveit = confirm('Sauvegarder la clé API pour les prochaines requêtes?');
        if (saveit) {
            localStorage.setItem('apiKey', apiKey);
        }
    }

    btn.disabled = true;
    btn.textContent = 'Migration en cours...';

    try {
        const response = await fetch(`${API_URL}/admin/migrate-logs-to-measurements`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            }
        });
        const data = await response.json();

        resultDiv.style.display = 'block';
        if (response.ok) {
            resultDiv.className = 'migration-result success';
            const stats = data.statistics;
            resultDiv.innerHTML = `
                <strong>✓ Migration réussie</strong><br/>
                <ul>
                    <li>Enregistrements importés: ${stats.imported}</li>
                    <li>Enregistrements ignorés (doublons): ${stats.skipped}</li>
                    <li>Total lu: ${stats.total_records}</li>
                    <li>Erreurs: ${stats.errors}</li>
                    <li>Fichiers traités: ${stats.files_processed}</li>
                </ul>
            `;
        } else if (response.status === 401) {
            resultDiv.className = 'migration-result error';
            resultDiv.textContent = '❌ Erreur d\'authentification: clé API invalide';
            localStorage.removeItem('apiKey'); // Remove invalid key
        } else {
            resultDiv.className = 'migration-result error';
            resultDiv.textContent = `❌ Erreur: ${data.detail}`;
        }
    } catch (error) {
        resultDiv.style.display = 'block';
        resultDiv.className = 'migration-result error';
        resultDiv.textContent = `❌ Erreur: ${error.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Programmer la migration';
        // Reload measurements data
        setTimeout(() => {
            loadMeasurements();
        }, 1000);
    }
}

async function loadDatabaseStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        const container = document.getElementById('db-stats-container');

        const latestReadable = data.latest_reading_timestamp ? new Date(data.latest_reading_timestamp).toLocaleString('fr-FR') : 'N/A';
        const oldestReadable = data.oldest_reading_timestamp ? new Date(data.oldest_reading_timestamp).toLocaleString('fr-FR') : 'N/A';
        const lastSyncReadable = data.latest_sync ? new Date(data.latest_sync).toLocaleString('fr-FR') : 'N/A';

        container.innerHTML = `
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">Total de lectures</div>
                    <div class="stat-value">${data.total_readings.toLocaleString('fr-FR')}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Appareils</div>
                    <div class="stat-value">${data.total_instruments}</div>
                </div>
            </div>
            <p><strong>Dernière lecture:</strong> ${latestReadable}</p>
            <p><strong>Première lecture:</strong> ${oldestReadable}</p>
            <p><strong>Dernière synchronisation:</strong> ${lastSyncReadable}</p>
        `;
    } catch (error) {
        console.error('Error loading database stats:', error);
    }
}

async function loadEvaporationRates() {
    try {
        const hours = document.getElementById('evap-hours').value || '24';
        const response = await fetch(`${API_URL}/evaporation-rate?hours=${hours}`);
        const data = await response.json();
        const container = document.getElementById('evap-rates-container');

        if (!data || data.length === 0) {
            container.innerHTML = '<p>Données insuffisantes pour calculer les taux d\'évaporation.</p>';
            return;
        }

        let html = `<table class="evap-table"><thead><tr>
            <th>Appareil</th>
            <th>Cryogène</th>
            <th>Taux (%/jour)</th>
            <th>Variation ${hours}h</th>
            <th>Niveau actuel</th>
            <th>Dernier remplissage</th>
        </tr></thead><tbody>`;

        data.forEach(rate => {
            const rateColor = rate.rate_percent_per_day < 0 ? '#10b981' : '#f59e0b';
            const refillStatus = rate.refill_detected
                ? `<small>${new Date(rate.last_refill_timestamp).toLocaleString('fr-FR', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}</small>`
                : '<small>Aucun détecté</small>';

            html += `<tr>
                <td><strong>${rate.device.toUpperCase()}</strong></td>
                <td>${rate.cryogen}</td>
                <td><span style="color: ${rateColor}">${rate.rate_percent_per_day.toFixed(2)}</span></td>
                <td>${rate.last_24h_change.toFixed(2)}%</td>
                <td>${rate.latest_level.toFixed(1)}%</td>
                <td>${refillStatus}</td>
            </tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading evaporation rates:', error);
    }
}


async function loadSyncHistory() {
    try {
        const response = await fetch(`${API_URL}/sync-history?limit=20`);
        const data = await response.json();
        const container = document.getElementById('sync-history-container');

        if (!data || data.length === 0) {
            container.innerHTML = '<p>Aucun historique de synchronisation.</p>';
            return;
        }

        let html = `<table class="sync-history-table"><thead><tr>
            <th>Date de début</th>
            <th>Durée</th>
            <th>Statut</th>
            <th>Lectures importées</th>
            <th>Fichiers</th>
        </tr></thead><tbody>`;

        data.forEach(record => {
            const startDate = new Date(record.started_at).toLocaleString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit',
                day: '2-digit',
                month: '2-digit'
            });
            const duration = ((new Date(record.completed_at) - new Date(record.started_at)) / 1000).toFixed(1);
            const statusBadge = `<span class="status-badge ${record.status}">${record.status.toUpperCase()}</span>`;

            html += `<tr>
                <td>${startDate}</td>
                <td>${duration}s</td>
                <td>${statusBadge}</td>
                <td>${record.total_imported}</td>
                <td>${record.files_processed}/${record.files_processed + record.files_failed}</td>
            </tr>`;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading sync history:', error);
    }
}

/**
 * Add evaporation rates to instrument cards
 */
async function loadEvaporationRatesForDashboard() {
    try {
        const response = await fetch(`${API_URL}/evaporation-rate?hours=24`);
        const rates = await response.json();

        // Create a map for quick lookup
        const rateMap = {};
        rates.forEach(rate => {
            const key = `${rate.device}-${rate.cryogen}`;
            rateMap[key] = rate.rate_percent_per_day;
        });

        // Add rates to each cryogen card
        document.querySelectorAll('.cryogen-reading').forEach(card => {
            const instrument = card.closest('[data-instrument]');
            const instrumentName = instrument?.getAttribute('data-instrument');
            const cryogen = card.getAttribute('data-cryogen');

            if (instrumentName && cryogen) {
                const key = `${instrumentName}-${cryogen}`;
                const rate = rateMap[key];
                const rateEl = card.querySelector('.evaporation-rate');
                if (rateEl && rate !== undefined) {
                    const rateText = rate < 0 ? `${Math.abs(rate).toFixed(2)}%/jour ↓` : `${rate.toFixed(2)}%/jour ↑`;
                    const rateColor = rate < 0 ? 'color: #10b981' : 'color: #f59e0b';
                    rateEl.innerHTML = `<small style="${rateColor}">${rateText}</small>`;
                }
            }
        });
    } catch (error) {
        console.error('Error loading evaporation rates for dashboard:', error);
    }
}

/**
 * Setup WebSocket connections for real-time updates
 */
function setupWebSocketConnections() {
    console.log('Setting up WebSocket connections for', instruments.length, 'instruments');
    instruments.forEach(instrument => {
        connectWebSocketForInstrument(instrument.name);
    });
}

/**
 * Connect WebSocket for a specific instrument
 */
function connectWebSocketForInstrument(instrumentName) {
    const wsUrl = `ws://${window.location.host}/api/ws/readings/${instrumentName}`;

    connectWebSocket(instrumentName, {
        onReading: (data) => {
            console.log(`New reading for ${instrumentName}:`, data);
            // Update the UI with new reading
            updateInstrumentCard(instrumentName, data);
        },
        onConnect: () => {
            console.log(`Connected to WebSocket for ${instrumentName}`);
            updateConnectionStatus(true);
        },
        onDisconnect: () => {
            console.log(`Disconnected from WebSocket for ${instrumentName}`);
            // Retry connection after 3 seconds
            setTimeout(() => connectWebSocketForInstrument(instrumentName), 3000);
        },
        onError: (error) => {
            console.error(`WebSocket error for ${instrumentName}:`, error);
            updateConnectionStatus(false);
        }
    });
}

/**
 * Update connection status indicator
 */
function setupConnectionStatusIndicator() {
    const statusEl = document.getElementById('connection-status');
    if (!statusEl) return;

    window.updateConnectionStatus = function(connected) {
        if (connected) {
            statusEl.classList.remove('disconnected');
            statusEl.classList.add('connected');
            statusEl.querySelector('.status-text').textContent = 'Connecté';
        } else {
            statusEl.classList.remove('connected');
            statusEl.classList.add('disconnected');
            statusEl.querySelector('.status-text').textContent = 'Déconnecté';
        }
    };
}

/**
 * Update instrument card with new reading
 */
function updateInstrumentCard(instrumentName, reading) {
    const card = document.querySelector(`[data-instrument="${instrumentName}"]`);
    if (!card) return;

    // Find the reading element for this cryogen
    const readingEl = Array.from(card.querySelectorAll('.cryogen-reading')).find(el => {
        return el.querySelector('.cryogen-name')?.textContent === reading.cryogen;
    });

    if (!readingEl) return;

    // Update level
    const levelValue = readingEl.querySelector('.level-value span:last-child');
    if (levelValue) {
        levelValue.textContent = reading.level.toFixed(1) + '%';
    }

    // Update level bar
    const levelFill = readingEl.querySelector('.level-fill');
    if (levelFill) {
        levelFill.style.width = reading.level + '%';
    }

    // Update timestamp
    const timeEl = readingEl.querySelector('.reading-time');
    if (timeEl) {
        const timestamp = new Date(reading.timestamp);
        const year = timestamp.getFullYear();
        const month = String(timestamp.getMonth() + 1).padStart(2, '0');
        const day = String(timestamp.getDate()).padStart(2, '0');
        const hour = String(timestamp.getHours()).padStart(2, '0');
        const minute = String(timestamp.getMinutes()).padStart(2, '0');
        const formattedTime = `${year}/${month}/${day} ${hour}:${minute}`;
        timeEl.textContent = formattedTime;
    }

    // Update status
    const statusClass = reading.status;
    readingEl.className = `cryogen-reading ${statusClass}`;
    const statusMsg = readingEl.querySelector('.status-indicator');
    if (statusMsg) {
        statusMsg.innerHTML = getStatusMessage(statusClass);
    }
}

/* ============================================
   MEASUREMENTS PAGE FUNCTIONS
   ============================================ */

// Type badge colors
const typeBadgeColors = {
    cryogen_level: "type-cryogen",
    temperature: "type-temperature",
    humidity: "type-humidity",
    pressure: "type-pressure",
    status: "type-status",
};

// Format timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });
}

// Load measurements
async function loadMeasurements() {
    const device = document.getElementById("filter-device").value;
    const location = document.getElementById("filter-location").value;
    const type = document.getElementById("filter-type").value;
    const hours = document.getElementById("filter-hours").value;

    // Show loading state
    document.getElementById("loading-state").style.display = "block";
    document.getElementById("measurements-table").style.display = "none";
    document.getElementById("empty-state").style.display = "none";
    document.getElementById("error-message").classList.remove("show");

    try {
        // Build query string
        const params = new URLSearchParams();
        if (device) params.append("device", device);
        if (location) params.append("location", location);
        if (type) params.append("measurement_type", type);
        params.append("hours", hours);
        params.append("limit", 500);

        const response = await fetch(`/api/measurements?${params}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const measurements = await response.json();

        // Update stats
        updateStats(measurements);

        // Populate table
        if (measurements.length === 0) {
            document.getElementById("empty-state").style.display = "block";
        } else {
            populateTable(measurements);
            document.getElementById("measurements-table").style.display = "table";
        }
    } catch (error) {
        console.error("Error loading measurements:", error);
        const errorDiv = document.getElementById("error-message");
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.classList.add("show");
    } finally {
        document.getElementById("loading-state").style.display = "none";
    }
}

// Update statistics
function updateStats(measurements) {
    // Total measurements
    document.getElementById("stat-total").textContent = measurements.length;

    // Unique types
    const types = new Set(measurements.map((m) => m.measurement_type));
    document.getElementById("stat-types").textContent = types.size;

    // Unique devices
    const devices = new Set(measurements.filter((m) => m.device).map((m) => m.device));
    document.getElementById("stat-devices").textContent = devices.size;
}

// Populate table with measurements
function populateTable(measurements) {
    const tbody = document.getElementById("table-body");
    tbody.innerHTML = "";

    measurements.forEach((m) => {
        const row = document.createElement("tr");
        const badgeClass = typeBadgeColors[m.measurement_type] || "type-status";
        const metadata = m.data ? JSON.stringify(m.data).substring(0, 50) : "—";

        row.innerHTML = `
            <td>${m.id}</td>
            <td>${m.device || "—"}</td>
            <td>${m.location || "—"}</td>
            <td><span class="type-badge ${badgeClass}">${m.measurement_type}</span></td>
            <td>${m.value !== null ? `${m.value} ${m.unit || ""}` : "—"}</td>
            <td class="timestamp">${formatTimestamp(m.timestamp)}</td>
            <td class="metadata" title="${metadata}">${metadata}</td>
        `;
        tbody.appendChild(row);
    });
}

// Apply filters
function applyFilters() {
    loadMeasurements();
}

// Clear filters
function clearFilters() {
    document.getElementById("filter-device").value = "";
    document.getElementById("filter-location").value = "";
    document.getElementById("filter-type").value = "";
    document.getElementById("filter-hours").value = "24";
    loadMeasurements();
}
