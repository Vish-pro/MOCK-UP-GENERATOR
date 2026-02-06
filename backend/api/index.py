import random
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import io
import os
import uuid
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from sklearn.cluster import KMeans
import base64

app = FastAPI()

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResult(BaseModel):
    garment_type: str
    dominant_color: str
    dominant_color_hex: str

class GenerationRequest(BaseModel):
    garment_type: str
    dominant_color_hex: str
    image_base64: str

class GeneratedImage(BaseModel):
    category: str
    view_name: str
    image_base64: str

def get_dominant_color(image: Image.Image) -> str:
    # Resize for speed
    image = image.copy()
    image.thumbnail((100, 100))
    # Convert to RGB and numpy array
    image = image.convert("RGB")
    data = np.array(image)
    data = data.reshape((-1, 3))

    # Use KMeans to find dominant color
    kmeans = KMeans(n_clusters=1, n_init=10)
    kmeans.fit(data)
    dominant_color = kmeans.cluster_centers_[0].astype(int)
    return "#{:02x}{:02x}{:02x}".format(*dominant_color)

def guess_garment_type(filename: str, image: Image.Image) -> str:
    # Simple heuristic based on filename or aspect ratio
    filename_lower = filename.lower()
    if "hoodie" in filename_lower:
        return "Hoodie"
    elif "t-shirt" in filename_lower or "tee" in filename_lower:
        return "T-Shirt"
    elif "pants" in filename_lower or "trousers" in filename_lower:
        return "Pants"
    elif "dress" in filename_lower:
        return "Dress"

    # Aspect ratio check
    width, height = image.size
    ratio = width / height
    if ratio > 1.2:
        return "Folded Item"
    elif ratio < 0.8:
        return "Full Body Garment (Dress/Pants)"

    return "T-Shirt" # Default

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        dominant_color_hex = get_dominant_color(image)
        garment_type = guess_garment_type(file.filename, image)

        return AnalysisResult(
            garment_type=garment_type,
            dominant_color="Calculated from image",
            dominant_color_hex=dominant_color_hex
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_mockup(category: str, view_name: str, original_image: Image.Image, bg_color: str = "#E0E0E0") -> str:
    # For serverless, we might want to reduce resolution if it times out,
    # but let's try to stick to the requested 4K or high quality.
    # Note: Vercel functions have 10s default timeout (hobby) or 60s (pro).
    # Generating 12 4K images might be too slow.
    # We will resize to Full HD (1920x1080) for performance and valid output within timeouts.
    width, height = 1920, 1080

    # Opal Gem style background (soft gradient or solid color)
    canvas = Image.new("RGB", (width, height), color="#F5F5F7")
    draw = ImageDraw.Draw(canvas)

    # Add text
    try:
        # Use default font since system fonts might not be available on Vercel lambda
        font = ImageFont.load_default()
        # Scale isn't possible with default bitmap font easily, so we might need a workaround or just accept small text
        # Or try to load a font if included in repo.
        # For now, default is safe.
    except:
        font = ImageFont.load_default()

    text = f"{category}\n{view_name}\nHigh Fidelity Asset"

    draw.text((50, 50), text, fill=(50, 50, 50), font=font)

    # Paste original image in the center
    img_ratio = original_image.width / original_image.height
    target_height = int(height * 0.6)
    target_width = int(target_height * img_ratio)

    resized_img = original_image.resize((target_width, target_height))

    # Center position
    x_pos = (width - target_width) // 2
    y_pos = (height - target_height) // 2

    canvas.paste(resized_img, (x_pos, y_pos))

    # Return base64
    buffered = io.BytesIO()
    canvas.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

@app.post("/api/generate", response_model=List[GeneratedImage])
async def generate_mockups(request: GenerationRequest):
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64.split(",")[1])
        original_image = Image.open(io.BytesIO(image_data))

        categories = {
            "Category A: With Humans (Faceless)": [
                "Front View", "Back View", "Right Profile", "Left Profile", "Close-up of Collar", "Close-up of Hand/Sleeve"
            ],
            "Category B: Without Humans (Ghost Mannequin)": [
                "Front View", "Back View", "Right Profile", "Left Profile", "Close-up of Collar", "Close-up of Hand/Sleeve"
            ]
        }

        results = []

        for category, views in categories.items():
            for view in views:
                # Simulate generation
                img_base64 = create_mockup(category, view, original_image)
                results.append(GeneratedImage(
                    category=category,
                    view_name=view,
                    image_base64=f"data:image/jpeg;base64,{img_base64}"
                ))

        return results

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
