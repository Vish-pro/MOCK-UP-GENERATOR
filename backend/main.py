import random
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Create static directory if it doesn't exist
os.makedirs("backend/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

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
    image_base64: str # Keeping the field name for frontend compatibility, but it will contain a URL

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

@app.post("/analyze", response_model=AnalysisResult)
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
    # 4K Resolution
    width, height = 3840, 2160

    # Opal Gem style background (soft gradient or solid color)
    canvas = Image.new("RGB", (width, height), color="#F5F5F7")
    draw = ImageDraw.Draw(canvas)

    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()

    text = f"{category}\n{view_name}\n4K Ultra HD Asset"

    draw.text((100, 100), text, fill=(50, 50, 50), font=font)

    # Paste original image in the center
    # Maintain aspect ratio
    img_ratio = original_image.width / original_image.height
    target_height = int(height * 0.6)
    target_width = int(target_height * img_ratio)

    resized_img = original_image.resize((target_width, target_height))

    # Center position
    x_pos = (width - target_width) // 2
    y_pos = (height - target_height) // 2

    canvas.paste(resized_img, (x_pos, y_pos))

    # Save to file instead of returning base64
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join("backend/static", filename)
    canvas.save(filepath, format="JPEG", quality=90)

    # Return URL
    return f"http://localhost:8000/static/{filename}"

@app.post("/generate", response_model=List[GeneratedImage])
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
                img_url = create_mockup(category, view, original_image)
                results.append(GeneratedImage(
                    category=category,
                    view_name=view,
                    image_base64=img_url # Using URL here
                ))

        return results

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
