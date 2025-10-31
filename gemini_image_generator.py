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
    # Try to import PersonGeneration enum if available
    try:
        from google.genai import types as genai_types
        PersonGeneration = genai_types.PersonGeneration
    except (ImportError, AttributeError):
        PersonGeneration = None
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
        person_generation: str = None,
        image_size: str = "1K"
    ) -> Optional[bytes]:
        """
        Generate an image using Gemini Imagen 4.0 API.
        
        Args:
            prompt: Description of the image to generate
            aspect_ratio: Image aspect ratio (16:9, 1:1, 9:16, 4:3, 3:4)
            output_mime_type: Output image format (image/jpeg, image/png)
            person_generation: Person generation setting (optional, omit if not supported)
            image_size: Image size (1K, 2K)
            
        Returns:
            Image bytes or None if generation fails
        """
        try:
            print(f"  📝 Generating image with prompt: {prompt[:100]}...")
            
            # Build config dict - only include person_generation if enum is available
            config_dict = {
                "number_of_images": 1,
                "output_mime_type": output_mime_type,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
            }
            
            print(f"  ⚙️  Config: {config_dict}")
            
            # Generate image using the SDK
            result = self.client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=config_dict,
            )
            
            print(f"  ✅ API call successful")
            print(f"  📊 Result type: {type(result)}")
            print(f"  📊 Result attributes: {dir(result)}")
            
            # Check if images were generated
            if not hasattr(result, 'generated_images') or not result.generated_images:
                print(f"⚠️  No images generated. Result: {result}")
                return None
            
            print(f"  📸 Found {len(result.generated_images)} generated images")
            
            if len(result.generated_images) != 1:
                print(f"⚠️  Expected 1 image, got {len(result.generated_images)}")
            
            # Get the first generated image
            generated_image = result.generated_images[0]
            print(f"  📸 Generated image type: {type(generated_image)}")
            print(f"  📸 Generated image attributes: {dir(generated_image)}")
            
            # Try different ways to access the image
            pil_image = None
            
            # Method 1: Check if .image attribute exists (PIL Image)
            if hasattr(generated_image, 'image'):
                pil_image = generated_image.image
                print(f"  ✅ Found .image attribute (PIL Image)")
            # Method 2: Check if .bytes attribute exists (raw bytes)
            elif hasattr(generated_image, 'bytes'):
                print(f"  ✅ Found .bytes attribute, returning directly")
                return generated_image.bytes
            # Method 3: Check if it's bytes directly
            elif isinstance(generated_image, bytes):
                print(f"  ✅ Generated image is bytes directly")
                return generated_image
            # Method 4: Check if it's a dict with image data
            elif isinstance(generated_image, dict):
                if 'image' in generated_image:
                    pil_image = generated_image['image']
                elif 'imageBase64' in generated_image:
                    import base64
                    image_bytes = base64.b64decode(generated_image['imageBase64'])
                    return image_bytes
                elif 'imageUrl' in generated_image:
                    import requests
                    img_response = requests.get(generated_image['imageUrl'], timeout=30)
                    img_response.raise_for_status()
                    return img_response.content
                else:
                    print(f"⚠️  Dict format but no known image key: {list(generated_image.keys())}")
                    return None
            else:
                print(f"⚠️  Unknown generated_image format: {type(generated_image)}")
                return None
            
            if not pil_image:
                print(f"⚠️  Could not extract PIL image from generated_image")
                return None
            
            print(f"  🖼️  PIL Image mode: {pil_image.mode}, size: {pil_image.size}")
            
            # Ensure image is in RGB mode for JPEG (convert RGBA/P to RGB if needed)
            if pil_image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background for transparency
                rgb_image = pil_image.convert('RGB')
                pil_image = rgb_image
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Determine format
            format_map = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/jpg': 'JPEG'
            }
            save_format = format_map.get(output_mime_type.lower(), 'JPEG')
            
            image_buffer = io.BytesIO()
            pil_image.save(image_buffer, format=save_format, quality=95)
            image_bytes = image_buffer.getvalue()
            
            print(f"  ✅ Successfully converted to bytes: {len(image_bytes)} bytes")
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
                # Leave placeholder as-is or add a comment (don't create broken img tag)
                # Option: Keep the placeholder so user knows image was intended
                # replacements.append((placeholder_info['placeholder'], f'<!-- Image generation failed: {description} -->'))
                # Option: Remove placeholder entirely
                replacements.append((placeholder_info['placeholder'], ''))
                continue
            
            # Upload to WordPress if requested
            if upload_to_wordpress and wp_publisher:
                try:
                    # Create a filename from the description
                    filename = self._create_filename_from_description(description, i)
                    
                    # Create SEO-friendly title and caption from description
                    # Title: Clean version of description (max 60 chars for SEO)
                    img_title = description[:60].rstrip('.')
                    # Caption: Full description (can be longer)
                    img_caption = description
                    # Alt text: Same as description (required for accessibility/SEO)
                    img_alt = description
                    # Description: Full description for media library
                    img_description = description
                    
                    # Upload image to WordPress
                    upload_result = wp_publisher.upload_image(
                        image_bytes=image_bytes,
                        filename=filename,
                        alt_text=img_alt,
                        title=img_title,
                        caption=img_caption,
                        description=img_description
                    )
                    
                    if upload_result and upload_result.get('url'):
                        img_url = upload_result['url']
                        img_id = upload_result.get('id')
                        
                        # Create WordPress-compatible img tag with proper SEO attributes
                        # Include alt text (required for SEO/accessibility)
                        # Include width/height for performance
                        # Include class for WordPress integration
                        img_tag = f'<img src="{img_url}" alt="{img_alt}" class="wp-image-{img_id}" width="800" height="450" />'
                        
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
