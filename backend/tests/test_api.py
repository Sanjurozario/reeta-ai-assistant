import uuid
import pytest
from starlette.testclient import TestClient
from app.main import app


def test_root_endpoint():
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "REETA"
        assert data["status"] == "operational"


def test_system_health_endpoint():
    with TestClient(app) as client:
        res = client.get("/api/v1/system/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["version"] == "1.0.0"


def test_system_models_endpoint():
    with TestClient(app) as client:
        res = client.get("/api/v1/system/models")
        assert res.status_code == 200
        data = res.json()
        assert "default_provider" in data
        assert "providers" in data
        assert "mock" in data["providers"]


def test_emergency_stop_endpoint():
    with TestClient(app) as client:
        res = client.post("/api/v1/system/emergency-stop")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "emergency stop executed" in data["message"].lower()


def test_task_creation_and_retrieval():
    with TestClient(app) as client:
        # Create Task
        payload = {
            "title": "API Test Task",
            "objective": "Verify endpoint contracts",
            "priority": 7,
        }
        create_res = client.post("/api/v1/tasks", json=payload)
        assert create_res.status_code == 201
        task_data = create_res.json()
        task_id = task_data["id"]
        assert task_data["title"] == "API Test Task"
        assert len(task_data["steps"]) == 3

        # Retrieve Task
        get_res = client.get(f"/api/v1/tasks/{task_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == task_id

        # Cancel Task
        cancel_res = client.post(f"/api/v1/tasks/{task_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "cancelled"


def test_websocket_stream_ping_pong():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/v1/stream") as websocket:
            # 1. Receive welcome frame
            welcome = websocket.receive_json()
            assert welcome["event"] == "connected"

            # 2. Send ping frame
            websocket.send_json({"event": "ping", "payload": {}})
            pong = websocket.receive_json()
            assert pong["event"] == "pong"

            # 3. Send user message frame
            websocket.send_json({"event": "user_message", "payload": {"text": "Hello REETA"}})
            thought = websocket.receive_json()
            assert thought["event"] == "agent_thought"
            response = websocket.receive_json()
            assert response["event"] == "agent_message"
            assert "content" in response["payload"]
