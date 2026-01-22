from fastapi.testclient import TestClient
from backend.main import app
import base64
from PIL import Image
import io

client = TestClient(app)

def create_test_image():
    image = Image.new("RGB", (100, 100), color="red")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()

def test_analyze():
    img_bytes = create_test_image()
    files = {"file": ("test.jpg", img_bytes, "image/jpeg")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "garment_type" in data
    assert "dominant_color_hex" in data

def test_generate():
    img_bytes = create_test_image()
    b64_img = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "garment_type": "T-Shirt",
        "dominant_color_hex": "#FF0000",
        "image_base64": f"data:image/jpeg;base64,{b64_img}"
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 12
    assert "image_base64" in data[0]
    assert "http" in data[0]["image_base64"]
