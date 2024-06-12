import pytest
import httpx
from fastapi.testclient import TestClient
from main import app, verify_signature
import hmac
import hashlib

# Use TestClient for synchronous tests, httpx.AsyncClient for asynchronous tests
client = TestClient(app)

# Example settings for testing
settings = {
    "POKESECRET_KEY": "your-secret-key",
    "pokeproxy_config": {
        "rules": [
            {
                "url": "http://localhost/receive",
                "reason": "awesome pokemon",
                "match": [
                    "hit_points==20",
                    "type_two != word",
                    "special_defense > 10",
                    "generation < 20"
                ]
            }
        ]
    }
}

def test_verify_signature():
    # Given
    secret_key = settings["POKESECRET_KEY"]
    request_body = b'test-body'
    received_signature = hmac.new(secret_key.encode(), request_body, hashlib.sha256).hexdigest()

    result = verify_signature(request_body, received_signature, secret_key.encode())

    assert result == True

@pytest.mark.asyncio
async def test_receive_pokemon(monkeypatch):
    monkeypatch.setattr("main.settings", settings)

    binary_data = b'\x08\xeb\x01\x12\x08Smeargle\x1a\x06Normal(\xfa\x01078\x14@#H\x14P-XK`\x02'

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/stream", content=binary_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["name"] == "Smeargle"
    assert json_response["hit_points"] == 20

@pytest.mark.asyncio
async def test_signature_verification(monkeypatch):
    monkeypatch.setattr("main.settings", settings)

    binary_data = b'\x08\xeb\x01\x12\x08Smeargle\x1a\x06Normal(\xfa\x01078\x14@#H\x14P-XK`\x02'
    secret_key = settings["POKESECRET_KEY"]
    received_signature = hmac.new(secret_key.encode(), binary_data, hashlib.sha256).hexdigest()

    headers = {
        "X-Grd-Signature": received_signature
    }

    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/stream", headers=headers, content=binary_data)

    assert response.status_code == 200