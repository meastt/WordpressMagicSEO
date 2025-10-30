"""
gemini_image_generator.py
==========================
Google Gemini image generation integration for automated content images.
"""

import os
import re
import io
import base64
from typing import List, Dict, Optional, Tuple

try:
    from google import genai
except ImportError:
    raise ImportError(
        "google-genai package is required. Install it with: pip install google-genai"
    )


class GeminiImageGenerator:
    """Generate images using Google Gemini Imagen 4.0 API and upload to WordPress."""
    
    def __init__(self, api_key: str = None):
        """Initialize with Google Gemini API key."""
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY required. Set it in environment variables.")
        
        # Initialize the Google GenAI client
        self.client = genai.Client(api_key=self.api_key)
        self.model = "models/imagen-4.0-generate-001"
    
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        output_mime_type: str = "image/jpeg",
        person_generation: str = "ALLOW_ALL",
        image_size: str = "1K"
    ) -> Optional[bytes]:
        """
        Generate an image using Gemini Imagen 4.0 API.
        
        Args:
            prompt: Description of the image to generate
            aspect_ratio: Image aspect ratio (16:9, 1:1, 9:16, 4:3, 3:4)
            output_mime_type: Output image format (image/jpeg, image/png)
            person_generation: Person generation setting (ALLOW_ALL, ALLOW_ADULT, BLOCK_ALL)
            image_size: Image size (1K, 2K)
            
        Returns:
            Image bytes or None if generation fails
        """
        try:
            # Generate image using the SDK
            result = self.client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=dict(
                    number_of_images=1,
                    output_mime_type=output_mime_type,
                    person_generation=person_generation,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                ),
            )
            
            # Check if images were generated
            if not result.generated_images:
                print("⚠️  No images generated.")
                return None
            
            if len(result.generated_images) != 1:
                print(f"⚠️  Expected 1 image, got {len(result.generated_images)}")
            
            # Get the first generated image
            generated_image = result.generated_images[0]
            
            # Convert image to bytes
            # The GeneratedImage object has an .image property (PIL Image)
            # We'll save it to a BytesIO buffer to get bytes
            image_buffer = io.BytesIO()
            generated_image.image.save(image_buffer, format=output_mime_type.split('/')[1].upper())
            image_bytes = image_buffer.getvalue()
            
            return image_bytes
            
        except Exception as e:
            print(f"⚠️  Error generating image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def enhance_prompt(self, base_description: str, article_title: str, keywords: List[str]) -> str:
        """
        Enhance image prompt with context for better results.
        
        Args:
            base_description: Original image description from placeholder
            article_title: Article title for context
            keywords: Article keywords for context
            
        Returns:
            Enhanced prompt for image generation
        """
        # Create a more detailed prompt
        enhanced = f"{base_description}. "
        enhanced += f"Professional, high-quality, realistic photograph. "
        enhanced += f"Related to: {article_title}. "
        
        if keywords:
            enhanced += f"Style: {', '.join(keywords[:3])}. "
        
        enhanced += "Well-lit, clear focus, suitable for blog content. "
        enhanced += "No text overlays, no watermarks."
        
        return enhanced
    
    def extract_image_placeholders(self, content: str) -> List[Dict[str, str]]:
        """
        Extract all [Image: description] placeholders from content.
        
        Args:
            content: HTML content with image placeholders
            
        Returns:
            List of dicts with 'placeholder', 'description', and 'position'
        """
        pattern = r'\[Image:\s*([^\]]+)\]'
        matches = []
        
        for match in re.finditer(pattern, content):
            matches.append({
                'placeholder': match.group(0),
                'description': match.group(1).strip(),
                'position': match.start()
            })
        
        return matches
    
    def replace_placeholders_with_images(
        self,
        content: str,
        article_title: str,
        keywords: List[str],
        wp_publisher=None,
        upload_to_wordpress: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Replace [Image: description] placeholders with actual generated images.
        
        Args:
            content: HTML content with image placeholders
            article_title: Article title for context
            keywords: Article keywords for context
            wp_publisher: WordPressPublisher instance for uploading images
            upload_to_wordpress: Whether to upload images to WordPress
            
        Returns:
            Tuple of (updated_content, list_of_image_info)
        """
        placeholders = self.extract_image_placeholders(content)
        
        if not placeholders:
            return content, []
        
        print(f"  🖼️  Found {len(placeholders)} image placeholders to generate")
        
        image_info_list = []
        replacements = []
        
        for i, placeholder_info in enumerate(placeholders):
            description = placeholder_info['description']
            enhanced_prompt = self.enhance_prompt(description, article_title, keywords)
            
            print(f"  🎨 Generating image {i+1}/{len(placeholders)}: {description[:50]}...")
            
            # Generate image
            image_bytes = self.generate_image(enhanced_prompt)
            
            if not image_bytes:
                print(f"  ⚠️  Failed to generate image for: {description}")
                # Replace with a simple alt text placeholder
                img_tag = f'<img src="" alt="{description}" class="generated-image-placeholder" />'
                replacements.append((placeholder_info['placeholder'], img_tag))
                continue
            
            # Upload to WordPress if requested
            if upload_to_wordpress and wp_publisher:
                try:
                    # Create a filename from the description
                    filename = self._create_filename_from_description(description, i)
                    
                    # Upload image to WordPress
                    upload_result = wp_publisher.upload_image(
                        image_bytes=image_bytes,
                        filename=filename,
                        alt_text=description,
                        title=description
                    )
                    
                    if upload_result and upload_result.get('url'):
                        img_url = upload_result['url']
                        img_id = upload_result.get('id')
                        
                        # Create WordPress-compatible img tag
                        img_tag = f'<img src="{img_url}" alt="{description}" class="wp-image-{img_id}" width="800" height="450" />'
                        
                        replacements.append((placeholder_info['placeholder'], img_tag))
                        
                        image_info_list.append({
                            'description': description,
                            'url': img_url,
                            'id': img_id,
                            'filename': filename
                        })
                        
                        print(f"  ✅ Image uploaded: {img_url}")
                    else:
                        # Fallback: embed as base64 (not ideal but works)
                        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" alt="{description}" />'
                        replacements.append((placeholder_info['placeholder'], img_tag))
                        
                except Exception as e:
                    print(f"  ⚠️  Error uploading image to WordPress: {e}")
                    # Fallback to base64 embedding
                    img_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" alt="{description}" />'
                    replacements.append((placeholder_info['placeholder'], img_tag))
            else:
                # No WordPress upload - embed as base64
                img_base64 = base64.b64encode(image_bytes).decode('utf-8')
                img_tag = f'<img src="data:image/jpeg;base64,{img_base64}" alt="{description}" />'
                replacements.append((placeholder_info['placeholder'], img_tag))
        
        # Replace all placeholders in reverse order (to preserve positions)
        updated_content = content
        for placeholder, img_tag in replacements:
            updated_content = updated_content.replace(placeholder, img_tag, 1)
        
        return updated_content, image_info_list
    
    def _create_filename_from_description(self, description: str, index: int) -> str:
        """Create a safe filename from image description."""
        # Clean description for filename
        filename = description.lower()
        filename = re.sub(r'[^a-z0-9\s-]', '', filename)
        filename = re.sub(r'\s+', '-', filename)
        filename = filename[:50]  # Limit length
        filename = filename.strip('-')
        
        # Add index if needed
        if index > 0:
            filename = f"{filename}-{index}"
        
        return f"{filename}.jpg"
