from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app

def run_all_tests():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/api/v1/health")
        print("1. Health check:", res.status_code, res.json())
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # 2. Upload a test study document
        test_file_content = (
            "Photosynthesis is a biological process used by plants and other organisms to convert light energy "
            "into chemical energy. Chemical equation: 6CO2 + 6H2O + light -> C6H12O6 + 6O2. "
            "Chlorophyll is the green pigment that absorbs solar photons primarily in the blue and red wavelengths. "
            "The light-dependent reactions occur in the thylakoid membranes of chloroplasts producing ATP and NADPH. "
            "The Calvin cycle occurs in the stroma where carbon dioxide is fixed into carbohydrates using RuBisCO enzyme."
        )
        files = {"file": ("photosynthesis_notes.txt", BytesIO(test_file_content.encode("utf-8")), "text/plain")}
        res = client.post("/api/v1/documents/upload", files=files)
        print("2. Upload document:", res.status_code)
        assert res.status_code == 201
        doc_data = res.json()["document"]
        doc_id = doc_data["id"]
        print("   Document ID:", doc_id)

        # 3. List documents
        res = client.get("/api/v1/documents")
        print("3. List documents count:", len(res.json()["documents"]))
        assert res.status_code == 200
        assert any(d["id"] == doc_id for d in res.json()["documents"])

        # 4. Get specific document
        res = client.get(f"/api/v1/documents/{doc_id}")
        print("4. Get document status:", res.status_code, "status:", res.json()["status"])
        assert res.status_code == 200

        # 5. Ask question (Explain mode)
        chat_payload = {
            "question": "What is the chemical equation for photosynthesis and where does the Calvin cycle occur?",
            "mode": "explain",
            "document_id": doc_id,
        }
        res = client.post("/api/v1/chat", json=chat_payload)
        print("5. Chat (Explain):", res.status_code)
        assert res.status_code == 200
        chat_resp = res.json()
        print("   Answer excerpt:", chat_resp["answer"][:120], "...")
        print("   Sources count:", len(chat_resp["sources"]))
        print("   Fallback status:", chat_resp["fallback"])

        # 6. Ask for a quiz
        quiz_payload = {
            "question": "Create a practice quiz on photosynthesis reactions",
            "mode": "quiz",
            "document_id": doc_id,
        }
        res = client.post("/api/v1/chat", json=quiz_payload)
        print("6. Chat (Quiz):", res.status_code)
        assert res.status_code == 200
        quiz_resp = res.json()
        print("   Quiz title:", quiz_resp.get("quiz", {}).get("title") if quiz_resp.get("quiz") else "Generated")

        # 7. Delete document
        res = client.delete(f"/api/v1/documents/{doc_id}")
        print("7. Delete document:", res.status_code, res.json())
        assert res.status_code == 200

        # Verify deletion
        res = client.get(f"/api/v1/documents/{doc_id}")
        assert res.status_code == 404
        print("   Verified document is removed (404).")

        # 8. Static frontend root & SPA fallback
        res = client.get("/")
        assert res.status_code == 200
        res = client.get("/quiz")
        assert res.status_code == 200
        print("8. Static files and SPA fallback verified.")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY WITH ZERO ERRORS!")

if __name__ == "__main__":
    run_all_tests()
