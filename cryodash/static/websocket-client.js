/**
 * WebSocket client for real-time cryogenic level updates.
 * Connects to /ws/readings/{instrument_id} and updates the UI in real-time.
 */

class ReadingsWebSocketClient {
    /**
     * Initialize the WebSocket client.
     * @param {string} instrumentId - The instrument ID to monitor
     * @param {Object} options - Configuration options
     * @param {Function} options.onReading - Callback when new reading received
     * @param {Function} options.onConnect - Callback on connection established
     * @param {Function} options.onDisconnect - Callback on disconnection
     * @param {Function} options.onError - Callback on error
     * @param {number} options.reconnectDelay - Delay before reconnect in ms (default: 3000)
     */
    constructor(instrumentId, options = {}) {
        this.instrumentId = instrumentId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = options.reconnectDelay || 3000;

        this.onReading = options.onReading || (() => {});
        this.onConnect = options.onConnect || (() => {});
        this.onDisconnect = options.onDisconnect || (() => {});
        this.onError = options.onError || (() => {});

        this.connect();
    }

    /**
     * Establish WebSocket connection.
     */
    connect() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const url = `${protocol}//${window.location.host}/api/ws/readings/${this.instrumentId}`;

        console.log(`Connecting to WebSocket: ${url}`);

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log(`WebSocket connected to ${this.instrumentId}`);
            this.reconnectAttempts = 0;
            this.onConnect();
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === "reading") {
                    console.log("New reading received:", message.data);
                    this.onReading(message.data);
                }
            } catch (e) {
                console.error("Error parsing WebSocket message:", e);
                this.onError(e);
            }
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
            this.onError(error);
        };

        this.ws.onclose = () => {
            console.log(
                `WebSocket disconnected from ${this.instrumentId}. ` +
                    `Reconnect attempts: ${this.reconnectAttempts}/${this.maxReconnectAttempts}`
            );
            this.onDisconnect();

            // Attempt to reconnect
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), this.reconnectDelay);
            } else {
                console.error(
                    `Max reconnect attempts reached for ${this.instrumentId}`
                );
            }
        };
    }

    /**
     * Send a ping message to keep connection alive.
     */
    ping() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send("ping");
        }
    }

    /**
     * Close the WebSocket connection.
     */
    close() {
        if (this.ws) {
            this.ws.close();
        }
    }

    /**
     * Check if connection is active.
     * @returns {boolean} True if connected
     */
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

/**
 * Global registry of active WebSocket clients.
 */
const wsClients = {};

/**
 * Connect to WebSocket for an instrument.
 * @param {string} instrumentId - The instrument ID
 * @param {Object} options - Client options
 * @returns {ReadingsWebSocketClient} The client instance
 */
function connectWebSocket(instrumentId, options = {}) {
    if (wsClients[instrumentId]) {
        console.warn(`WebSocket already connected for ${instrumentId}`);
        return wsClients[instrumentId];
    }

    const client = new ReadingsWebSocketClient(instrumentId, options);
    wsClients[instrumentId] = client;
    return client;
}

/**
 * Disconnect from WebSocket for an instrument.
 * @param {string} instrumentId - The instrument ID
 */
function disconnectWebSocket(instrumentId) {
    if (wsClients[instrumentId]) {
        wsClients[instrumentId].close();
        delete wsClients[instrumentId];
    }
}

/**
 * Disconnect all active WebSocket clients.
 */
function disconnectAllWebSockets() {
    Object.values(wsClients).forEach((client) => client.close());
    Object.keys(wsClients).forEach((key) => delete wsClients[key]);
}

// Export for use in modules
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        ReadingsWebSocketClient,
        connectWebSocket,
        disconnectWebSocket,
        disconnectAllWebSockets,
        wsClients,
    };
}
