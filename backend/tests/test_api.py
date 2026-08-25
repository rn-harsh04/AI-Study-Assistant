from fastapi.testclient import TestClient
from app.main import app

def test_endpoints():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # 2. List documents
        res = client.get("/api/v1/documents")
        assert res.status_code == 200

        # 3. Static frontend root
        res = client.get("/")
        assert res.status_code == 200

        # 4. SPA route fallback
        res = client.get("/chat")
        assert res.status_code == 200

if __name__ == "__main__":
    test_endpoints()
    print("All endpoint tests passed successfully!")