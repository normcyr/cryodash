"""Tests for WebSocket functionality."""


def test_websocket_connect(client, test_db):
    """Test WebSocket connection."""
    with client.websocket_connect("/api/ws/readings/neo600") as websocket:
        # Should receive welcome message or latest reading
        data = websocket.receive_json()
        assert "type" in data
        assert data["type"] == "reading"


def test_websocket_receive_reading(client, test_db):
    """Test receiving a reading through WebSocket."""
    # First create a reading via API
    resp = client.post(
        "/api/readings",
        json={
            "device": "test_neo",
            "cryogen": "N2",
            "level": 85.0,
        },
    )
    assert resp.status_code == 200

    # Connect to WebSocket
    with client.websocket_connect("/api/ws/readings/test_neo") as websocket:
        # Should receive the latest reading
        data = websocket.receive_json()
        assert data["type"] == "reading"
        assert data["data"]["device"] == "test_neo"
        assert data["data"]["level"] == 85.0


def test_websocket_ping_pong(client, test_db):
    """Test ping/pong keep-alive."""
    with client.websocket_connect("/api/ws/readings/neo600") as websocket:
        # Receive initial data
        websocket.receive_json()

        # Send ping
        websocket.send_text("ping")

        # Should receive pong
        response = websocket.receive_text()
        assert response == "pong"


def test_websocket_multiple_connections(client, test_db):
    """Test multiple simultaneous WebSocket connections."""
    # Create readings first
    for device in ["ws_test_1", "ws_test_2"]:
        client.post(
            "/api/readings",
            json={
                "device": device,
                "cryogen": "N2",
                "level": 75.0,
            },
        )

    connections = [
        client.websocket_connect("/api/ws/readings/ws_test_1"),
        client.websocket_connect("/api/ws/readings/ws_test_2"),
    ]

    try:
        for ctx in connections:
            ws = ctx.__enter__()
            data = ws.receive_json()
            assert data["type"] == "reading"
            assert "data" in data
    finally:
        for ctx in connections:
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                pass


def test_websocket_separation(client, test_db):
    """Test that WebSocket streams are properly separated by instrument."""
    # Create readings for two unique instruments
    client.post(
        "/api/readings",
        json={
            "device": "isolated_1",
            "cryogen": "N2",
            "level": 80.0,
        },
    )
    client.post(
        "/api/readings",
        json={
            "device": "isolated_2",
            "cryogen": "He",
            "level": 90.0,
        },
    )

    # Connect to isolated_1 and verify device name
    with client.websocket_connect("/api/ws/readings/isolated_1") as ws1:
        data = ws1.receive_json()
        assert data["data"]["device"] == "isolated_1"
        assert data["data"]["level"] == 80.0

    # Connect to isolated_2 and verify device name
    with client.websocket_connect("/api/ws/readings/isolated_2") as ws2:
        data = ws2.receive_json()
        assert data["data"]["device"] == "isolated_2"
        assert data["data"]["level"] == 90.0
