import os
import io
import base64
import random
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import google.generativeai as genai
from dotenv import load_dotenv
import replicate
import traceback

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Configure Replicate
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token

app = FastAPI()

# Allow CORS
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
    ai_analysis: Optional[str] = None

class GenerationRequest(BaseModel):
    garment_type: str
    dominant_color_hex: str
    front_image_base64: str
    back_image_base64: Optional[str] = None

class GeneratedImage(BaseModel):
    category: str
    view_name: str
    image_base64: str

class GenerationResponse(BaseModel):
    mockups: List[GeneratedImage]
    ai_analysis: Optional[str] = None

def get_dominant_color(image: Image.Image) -> str:
    # Use Pillow's quantization to find dominant color (lightweight)
    image = image.copy()
    image.thumbnail((150, 150))
    # Quantize to 1 color to find the dominant one
    q_img = image.quantize(colors=1)
    # Get palette
    palette = q_img.getpalette()
    if palette:
        r, g, b = palette[:3]
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
    return "#000000"

def guess_garment_type(filename: str, image: Image.Image) -> str:
    filename_lower = filename.lower()
    if "hoodie" in filename_lower:
        return "Hoodie"
    elif "t-shirt" in filename_lower or "tee" in filename_lower:
        return "T-Shirt"
    elif "pants" in filename_lower or "trousers" in filename_lower:
        return "Pants"
    elif "dress" in filename_lower:
        return "Dress"

    width, height = image.size
    ratio = width / height
    if ratio > 1.2:
        return "Folded Item"
    elif ratio < 0.8:
        return "Full Body Garment (Dress/Pants)"

    return "T-Shirt"

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

        # Get AI analysis during the check step too
        # Convert to base64 for Gemini
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        ai_analysis = await get_gemini_analysis(img_b64)

        return AnalysisResult(
            garment_type=garment_type,
            dominant_color="Calculated from image",
            dominant_color_hex=dominant_color_hex,
            ai_analysis=ai_analysis
        )
    except Exception as e:
        print(f"Error in analyze: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def create_mockup(category: str, view_name: str, original_image: Image.Image, garment_type: str) -> str:
    # Resize to High Quality
    width, height = 2048, 2048 # 2K Square for premium feel

    # Create a more realistic background (Gradients/Soft Studio)
    canvas = Image.new("RGB", (width, height), color="#FFFFFF")
    
    # Simple Studio Gradient
    for i in range(height):
        # Very subtle grey gradient
        color_val = 245 - int((i / height) * 10)
        for j in range(width):
            canvas.putpixel((j, i), (color_val, color_val, color_val + 2))

    draw = ImageDraw.Draw(canvas)

    # Remove background from original if it's not transparent (simple attempt)
    # For now, we assume the user uploads a decent image, but we add a soft shadow
    
    img = original_image.convert("RGBA")
    
    # Calculate scale
    img_ratio = img.width / img.height
    target_height = int(height * 0.7)
    target_width = int(target_height * img_ratio)
    
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Create Shadow
    shadow_width = int(target_width * 1.05)
    shadow_height = int(target_height * 0.05)
    shadow = Image.new("RGBA", (shadow_width, shadow_height), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(shadow)
    sh_draw.ellipse([0, 0, shadow_width, shadow_height], fill=(0, 0, 0, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))

    # Paste Shadow
    canvas.paste(shadow, ((width - shadow_width)//2, (height + target_height)//2 - 20), shadow)

    # Paste Image
    x_pos = (width - target_width) // 2
    y_pos = (height - target_height) // 2
    canvas.paste(img, (x_pos, y_pos), img if img.mode == 'RGBA' else None)

    # Add Branding/Text with better font handling
    try:
        # Try to find a nice font on Windows
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    # label = f"{garment_type.upper()} | {view_name.upper()}"
    # draw.text((width//2, height - 100), label, fill=(100, 100, 100), anchor="mm", font=font)

    buffered = io.BytesIO()
    canvas.save(buffered, format="JPEG", quality=90)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

async def get_gemini_analysis(image_base64: str):
    if not api_key:
        return None
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Prepare image for Gemini
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        
        image_parts = [
            {
                "mime_type": "image/png",
                "data": image_base64
            }
        ]
        
        prompt = "Analyze this garment. Identify its type, material, color, and key features (e.g., hood, pockets). " \
                 "Also suggest a premium lifestyle background description for a professional mockup."
        
        response = model.generate_content([prompt, image_parts[0]])
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

async def generate_realistic_mockup_with_replicate(category: str, view_name: str, original_image: Image.Image, garment_type: str, dominant_color: str) -> Optional[str]:
    """Generate realistic fashion mockup using Replicate + Stable Diffusion."""
    if not replicate_token:
        print("No Replicate token, falling back to placeholder")
        return None
    
    try:
        # Determine if we need a human model or ghost mannequin
        is_human_category = "With Humans" in category
        
        # Craft detailed prompt based on view and category
        if is_human_category:
            model_desc = "faceless fashion model, no face visible, head cropped or turned away"
        else:
            model_desc = "ghost mannequin effect, invisible model, floating garment"
        
        # View-specific prompts
        view_prompts = {
            "Front View": "front view, centered, straight-on angle",
            "Back View": "back view, rear angle, showing the back clearly",
            "Right Profile": "right side profile, 90-degree angle",
            "Left Profile": "left side profile, 90-degree angle",
            "Close-up of Collar": "extreme close-up of collar and neckline, detailed texture",
            "Close-up of Hand/Sleeve": "close-up of sleeve and hand, fabric detail visible"
        }
        
        view_detail = view_prompts.get(view_name, "front view")
        
        # Construct the prompt
        prompt = f"""Professional e-commerce product photography, {garment_type} in {dominant_color} color, {view_detail}, {model_desc}, clean white studio background, soft professional lighting, high-resolution 4K quality, fashion catalog style, premium commercial photography, photorealistic"""
        
        negative_prompt = "face, facial features, eyes, nose, mouth, text, watermark, logo, low quality, distorted, blurry, amateur"
        
        print(f"Generating mockup with Replicate: {view_name}")
        print(f"Prompt: {prompt[:100]}...")
        
        # Use SDXL for high-quality fashion photography
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": 1024,
                "height": 1024,
                "num_outputs": 1,
                "guidance_scale": 7.5,
                "num_inference_steps": 50,
                "scheduler": "K_EULER"
            }
        )
        
        # Output is a list of URLs
        if output and len(output) > 0:
            image_url = output[0]
            print(f"Generated image URL: {image_url}")
            
            # Download the image and convert to base64
            response = requests.get(image_url)
            if response.status_code == 200:
                img_base64 = base64.b64encode(response.content).decode("utf-8")
                return img_base64
        
        return None
        
    except Exception as e:
        print(f"Replicate error: {e}")
        traceback.print_exc()
        return None


@app.post("/api/generate", response_model=GenerationResponse)
async def generate_mockups(request: GenerationRequest):
    try:
        # Decode front image
        if "," in request.front_image_base64:
            front_data = base64.b64decode(request.front_image_base64.split(",")[1])
        else:
            front_data = base64.b64decode(request.front_image_base64)
        front_image = Image.open(io.BytesIO(front_data))

        # Decode back image if provided, otherwise fallback to front
        back_image = front_image
        if request.back_image_base64:
            if "," in request.back_image_base64:
                back_data = base64.b64decode(request.back_image_base64.split(",")[1])
            else:
                back_data = base64.b64decode(request.back_image_base64)
            back_image = Image.open(io.BytesIO(back_data))

        # Optional: Use Gemini to enhance analysis if available
        ai_analysis = await get_gemini_analysis(request.front_image_base64)
        if ai_analysis:
            print(f"AI Analysis: {ai_analysis}")

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
                # Use back image for "Back View", front for others
                target_image = back_image if "Back View" in view else front_image
                
                # Try to generate realistic mockup with Replicate
                ai_generated_img = await generate_realistic_mockup_with_replicate(
                    category, view, target_image, request.garment_type, request.dominant_color_hex
                )
                
                if ai_generated_img:
                    # Use AI-generated mockup
                    results.append(GeneratedImage(
                        category=category,
                        view_name=view,
                        image_base64=f"data:image/jpeg;base64,{ai_generated_img}"
                    ))
                else:
                    # Fallback to placeholder mockup
                    img_base64 = create_mockup(category, view, target_image, request.garment_type)
                    results.append(GeneratedImage(
                        category=category,
                        view_name=view,
                        image_base64=f"data:image/jpeg;base64,{img_base64}"
                    ))

        return {
            "mockups": results,
            "ai_analysis": ai_analysis
        }

    except Exception as e:
        print(f"Error in generate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
