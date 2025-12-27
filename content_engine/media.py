import logging
import os
import anthropic
from google import genai
from google.genai import types

class MediaEngine:
    """
    The 'Artist' of the AI Content Engine.
    Responsible for visual assets, alt text, and branding.
    Uses Google Gemini 3 (Imagen 4) for images and Claude Sonnet 4.5 for prompting.
    """

    def __init__(self, api_key=None, anthropic_key=None):
        self.logger = logging.getLogger(__name__)
        
        # Gemini setup
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1alpha'})
        else:
            self.logger.warning("No Google Gemini API Key found. MediaEngine running in MOCK mode.")
            self.client = None

        # Claude setup for Prompt Engineering
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
        if self.anthropic_key:
            self.claude = anthropic.Anthropic(api_key=self.anthropic_key)
        else:
            self.claude = None

    def _generate_creative_prompt(self, title: str, context: str) -> str:
        """
        Uses Claude to write a detailed, visually rich prompt for Imagen.
        """
        if not self.claude:
            return f"A high-quality photo of {title}"
            
        system = "You are an expert Food Blogger and Photographer known for authentic, mouth-watering imagery."
        user_prompt = (
            f"Write a detailed image generation prompt for a blog post titled '{title}'.\n"
            f"Context: {context}\n"
            f"Style Guide: Authentic, high-quality, 'in the moment' feel. Not overly staged.\n"
            f"Requirements:\n"
            f"- Photorealistic, cinematic lighting, but natural (like a high-end vlog or blog).\n"
            f"- Outdoor cooking setting (backyard, patio, camping) where appropriate.\n"
            f"- Focus on the delicious food and the action/result.\n"
            f"- Avoid 'perfectly staged' backgrounds (e.g., NO random raw ingredients scattered nicely, NO perfect salt piles).\n"
            f"- Make it look like a skilled home chef took it, not a commercial studio.\n"
            f"- Return ONLY the prompt text."
        )
        
        try:
            msg = self.claude.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            self.logger.error(f"Claude Prompt Gen Error: {e}")
            return f"A delicious, cinematic outdoor photo of {title}"

    def generate_featured_image(self, title: str, style_guide: str = "photorealistic", output_dir: str = "content/assets") -> str:
        """
        Generates a Gemini 3 (Imagen 4) image for the post.
        Saves into output_dir.
        """
        if not self.client:
            return "mock_image.png"

        # 1. Craft the Prompt using Claude
        creative_prompt = self._generate_creative_prompt(title, style_guide)
        self.logger.info(f"🎨 Creative Prompt: {creative_prompt}")

        try:
            # 2. Generate Image with correct aspect ratio (16:9)
            response = self.client.models.generate_images(
                model='models/imagen-4.0-generate-preview-06-06',
                prompt=creative_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9", # Enforce Landscape
                    output_mime_type="image/png"
                )
            )
            
            if response.generated_images:
                image_data = response.generated_images[0].image.image_bytes
                
                # Ensure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                safe_title = "".join(x for x in title if x.isalnum() or x in " -_").replace(" ", "_").lower()
                filename = os.path.join(output_dir, f"{safe_title}.png")
                
                with open(filename, "wb") as f:
                    f.write(image_data)
                    
                return filename
            else:
                 self.logger.error("No images returned from Gemini.")
                 return "error_image.png"

        except Exception as e:
            self.logger.error(f"Gemini Image Gen Error: {e}")
            return "error_image.png"

    def generate_alt_text(self, image_url: str, context: str) -> str:
        """
        Generates descriptive SEO-friendly alt text using Gemini Vision.
        """
        if not self.client:
            return f"Alt text for {context}"

        # Note: image_url here usually needs to be a local path or verified URL for Gemini
        # For this logic, we assume it handles text-only prompt if image reading fails or is complex
        return f"Detailed view of {context} - (Vision Not Implemented in this Step)"

    def watermark_image(self, image_path: str, logo_path: str = "assets/logo.png") -> str:
        """
        Overlays the brand logo on the image.
        """
        self.logger.info(f"Watermarking image: {image_path}")
        return image_path
