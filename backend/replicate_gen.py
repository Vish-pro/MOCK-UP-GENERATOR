async def generate_realistic_mockup_with_replicate(category: str, view_name: str, original_image: Image.Image, garment_type: str, dominant_color: str) -> Optional[str]:
    """Generate realistic fashion mockup using Replicate + Stable Diffusion."""
    if not replicate_token:
        print("No Replicate token, falling back to placeholder")
        return None
    
    try:
        # Convert image to base64 for reference
        buffered = io.BytesIO()
        original_image.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        img_data_uri = f"data:image/png;base64,{img_b64}"
        
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
            import requests
            response = requests.get(image_url)
            if response.status_code == 200:
                img_base64 = base64.b64encode(response.content).decode("utf-8")
                return img_base64
        
        return None
        
    except Exception as e:
        print(f"Replicate error: {e}")
        import traceback
        traceback.print_exc()
        return None
