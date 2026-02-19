#!/usr/bin/env python3
"""Test script for POST /api/data endpoint"""

import json

import requests

API_KEY = "dev-key-change-in-production"
BASE_URL = "http://localhost:8000"


def test_single_reading():
    """Test 1: Single cryogen reading"""
    print("\n=== Test 1: Single Cryogen Reading ===")

    url = f"{BASE_URL}/api/data"
    data = {
        "device": "neo600",
        "timestamp": "2026-02-17T10:30:00Z",
        "readings": [{"type": "cryogen_level", "cryogen": "N2", "value": 85.5, "unit": "%"}],
    }

    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    response = requests.post(url, json=data, headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

    return response.status_code == 200


def test_multiple_readings():
    """Test 2: Multiple readings with locations"""
    print("\n=== Test 2: Multiple Readings with Locations ===")

    url = f"{BASE_URL}/api/data"
    data = {
        "device": "neo600",
        "location": "magnet_room",
        "timestamp": "2026-02-17T11:00:00Z",
        "readings": [
            {"type": "cryogen_level", "cryogen": "N2", "value": 82.3, "unit": "%"},
            {"type": "temperature", "location": "sample_room", "value": 23.5, "unit": "°C"},
            {"type": "humidity", "value": 48.2, "unit": "%"},
        ],
    }

    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    response = requests.post(url, json=data, headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

    return response.status_code == 200


def test_independent_reading():
    """Test 3: Independent reading (no device/location)"""
    print("\n=== Test 3: Independent Reading (No Device/Location) ===")

    url = f"{BASE_URL}/api/data"
    data = {
        "timestamp": "2026-02-17T11:15:00Z",
        "readings": [
            {
                "type": "pressure",
                "value": 101.325,
                "unit": "kPa",
                "metadata": {"sensor": "barometric_001", "calibration_date": "2026-01-15"},
            }
        ],
    }

    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    response = requests.post(url, json=data, headers=headers, timeout=5)
    print(f"Status: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

    return response.status_code == 200


def test_health_check():
    """Test 4: Health check endpoint"""
    print("\n=== Test 4: Health Check ===")

    url = f"{BASE_URL}/api/health"
    response = requests.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

    return response.status_code == 200


if __name__ == "__main__":
    print("Starting API tests...")

    # Test health first
    if not test_health_check():
        print("❌ Server is not responding!")
        exit(1)

    print("\n✅ Server is running!\n")

    results = {
        "Test 1 (Single Reading)": test_single_reading(),
        "Test 2 (Multiple Readings)": test_multiple_readings(),
        "Test 3 (Independent Reading)": test_independent_reading(),
    }

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed")
