"""
claude_content_generator.py
===========================
Enhanced content generator using Claude API for intelligent, research-based content creation.
"""

import os
import anthropic
from typing import List, Dict
import time
import re


class ClaudeContentGenerator:
    """Generate high-quality content using Claude API with web research."""
    
    def __init__(self, api_key: str = None):
        """Initialize with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def research_topic(self, topic_title: str, keywords: List[str]) -> str:
        """Use Claude with web search to research a topic thoroughly."""
        from datetime import datetime
        current_date = datetime.now().strftime('%B %d, %Y')

        prompt = f"""IMPORTANT: Use web search to find current, up-to-date information about this topic.

Research the topic "{topic_title}" focusing on these keywords: {', '.join(keywords)}.

Today's date is {current_date}. Search for information from the last 6-12 months.

Using web search, provide:
1. **Current market trends** - What's happening NOW in this space (search for recent articles, reviews, discussions)
2. **Latest product releases or updates** - Any new developments in the last 6 months
3. **What people are searching for** - Current search trends and questions
4. **Key facts and data points** - Statistics, prices, specifications (verify with searches)
5. **Top competing content** - What are the best articles/guides ranking for these keywords
6. **Common questions** - What are people asking on forums, Reddit, review sites

**Critical: Actually search the web for each of these points. Cite specific sources with URLs and dates.**

Format your research with clear sections and bullet points. Include source URLs where possible."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            thinking={
                "type": "enabled",
                "budget_tokens": 2000
            }
        )

        # Extract text from response (handle thinking blocks)
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text

        return response_text
    
    def generate_article(
        self,
        topic_title: str,
        keywords: List[str],
        research: str,
        meta_description: str,
        existing_content: str = None,
        internal_links: List[Dict] = None,
        affiliate_links: List[Dict] = None,
        competitive_brief: str = None,
        quality_requirements: Dict = None
    ) -> Dict[str, str]:
        """
        Generate complete article with metadata and affiliate links.

        Enhanced with competitive intelligence and quality requirements.

        Args:
            topic_title: Article title
            keywords: Target keywords
            research: Research data from research_topic()
            meta_description: Base meta description
            existing_content: Existing content to update (optional)
            internal_links: Internal links to include
            affiliate_links: Affiliate links to include
            competitive_brief: Output from CompetitiveAnalyzer (NEW!)
            quality_requirements: Specific quality requirements (NEW!)

        Returns:
            Dict with title, content, categories, tags, meta, schema
        """

        # Get current date for context with seasonal awareness
        from datetime import datetime
        current_date = datetime.now()

        # Determine season and time of year context
        month = current_date.month
        day = current_date.day

        # Determine season
        if month in [12, 1, 2]:
            season = "winter"
            season_desc = "the cold winter months"
        elif month in [3, 4, 5]:
            season = "spring"
            season_desc = "the fresh spring season"
        elif month in [6, 7, 8]:
            season = "summer"
            season_desc = "the warm summer months"
        else:  # 9, 10, 11
            season = "fall/autumn"
            season_desc = "the fall season"

        # Determine time of year context for language
        if month == 1 and day <= 15:
            time_context = "early in the new year - phrases like 'kick off the year' or 'start the year right' are appropriate"
        elif month == 1:
            time_context = "late January - still appropriate to reference the new year, but avoid 'kicking off'"
        elif month == 2:
            time_context = "mid-winter - focus on current season, not new year language"
        elif month in [3, 4]:
            time_context = "spring - perfect for renewal, fresh starts, spring cleaning themes"
        elif month in [5, 6]:
            time_context = "late spring/early summer - outdoor activities, warm weather themes"
        elif month in [7, 8]:
            time_context = "peak summer - vacation, outdoor cooking, warm weather focus"
        elif month == 9:
            time_context = "early fall - back to school, routine, transition themes"
        elif month == 10:
            time_context = "mid-fall - Halloween, autumn harvest, cozy themes"
        elif month == 11:
            time_context = "late fall - Thanksgiving, holiday prep, gratitude themes"
        elif month == 12 and day <= 20:
            time_context = "holiday season - Christmas, Hanukkah, winter celebrations"
        else:
            time_context = "end of year - year-end reflections, New Year prep"

        date_context = f"\n\n{'='*80}\n⏰ CRITICAL TEMPORAL CONTEXT - READ CAREFULLY:\n{'='*80}\n"
        date_context += f"📅 TODAY'S DATE: {current_date.strftime('%B %d, %Y')} (Month: {current_date.strftime('%B')}, Year: {current_date.year})\n"
        date_context += f"🌡️  SEASON: {season.title()} - {season_desc}\n"
        date_context += f"📆 TIME OF YEAR: {time_context}\n"
        date_context += f"\n{'='*80}\n"
        date_context += "⚠️  CONTEXTUAL LANGUAGE REQUIREMENTS:\n"
        date_context += "- Use language appropriate for the CURRENT time of year\n"
        date_context += "- Do NOT use 'kick off the year' or 'start the year right' unless it's early January\n"
        date_context += "- Reference the current season naturally in your writing\n"
        date_context += "- For year references in titles, use the current year (2025)\n"
        date_context += "- Match the mood and themes appropriate for this time of year\n"
        date_context += f"{'='*80}\n"

        action = "update this existing content" if existing_content else "create new content"
        existing_context = f"\n\nEXISTING CONTENT TO UPDATE:\n{existing_content}" if existing_content else ""
        
        internal_links_text = ""
        if internal_links:
            internal_links_text = "\n\nINTERNAL LINKS to include naturally:\n"
            for link in internal_links:
                internal_links_text += f"- {link['title']}: {link['url']}\n"
        
        affiliate_links_text = ""
        if affiliate_links:
            affiliate_links_text = "\n\nAFFILIATE PRODUCT LINKS to include naturally:\n"
            for link in affiliate_links:
                affiliate_links_text += f"- {link['brand']} {link['product_name']} ({link['product_type']}): {link['url']}\n"

        # NEW: Competitive intelligence context
        competitive_context = ""
        if competitive_brief:
            competitive_context = f"\n\n{'='*80}\n🎯 COMPETITIVE INTELLIGENCE (CRITICAL - FOLLOW THIS):\n{'='*80}\n{competitive_brief}\n{'='*80}\n"

        # NEW: Quality requirements context
        quality_context = ""
        if quality_requirements:
            quality_context = f"\n\n📊 QUALITY REQUIREMENTS:\n"
            quality_context += f"- Target Word Count: {quality_requirements.get('min_word_count', 2000):,} words minimum\n"
            quality_context += f"- E-E-A-T Score Target: {quality_requirements.get('eeat_score', 8)}/10+\n"
            quality_context += f"- Must Include: {', '.join(quality_requirements.get('must_include', []))}\n"

        # Detect if this is a list/recipe article that needs completeness checking
        import re
        list_match = re.search(r'(\d+)\s*(recipes?|ideas?|ways?|tips?|methods?)', topic_title.lower())
        completeness_reminder = ""
        if list_match:
            expected_count = int(list_match.group(1))
            item_type = list_match.group(2).rstrip('s')  # singular form
            completeness_reminder = f"""
{'='*80}
🚨 CRITICAL COMPLETENESS REQUIREMENT - READ CAREFULLY:
{'='*80}
This article PROMISES {expected_count} {list_match.group(2)}. You MUST deliver ALL {expected_count} COMPLETE {list_match.group(2)}.

Each {item_type} MUST include:
- A clear title/heading (H3 or H4)
- Full, detailed content (at least 150-200 words per {item_type})
- If it's a recipe: ingredients list AND preparation steps
- If it's a method/tip: detailed explanation with examples
- Specific, actionable information - NO placeholders or "coming soon" text

⚠️  DO NOT create incomplete {list_match.group(2)} with just a title and intro line!
⚠️  DO NOT stop at {expected_count//2} {list_match.group(2)} - you must complete ALL {expected_count}!
⚠️  Each {item_type} should be substantial and valuable on its own.

Quality control will verify that all {expected_count} {list_match.group(2)} are complete.
{'='*80}
"""

        prompt = f"""You are an ELITE SEO content writer. {action.capitalize()} about: "{topic_title}"
{date_context}

TARGET KEYWORDS: {', '.join(keywords)}

RESEARCH DATA:
{research}
{existing_context}
{internal_links_text}
{affiliate_links_text}
{competitive_context}
{quality_context}
{completeness_reminder}

Create a comprehensive, SUPERIOR article that:
1. **BEATS COMPETITORS**: If competitive brief is provided, your content MUST be MORE comprehensive, better structured, and more valuable than top-ranking content
2. Uses natural, engaging writing (not robotic)
3. Includes the target keywords naturally (don't force them)
4. Provides genuine value to readers with specific examples and actionable advice
5. **DO NOT include external links** - AI cannot verify URLs exist, causing 404 errors
6. Naturally weaves in the provided internal links where relevant
7. Naturally incorporates affiliate product links where they add value (don't force them)
8. Uses proper HTML formatting (h2, h3, p, ul, ol, strong, em, tables)
9. **Follows competitive brief precisely** (if provided) - cover ALL missing topics
10. Includes multimedia suggestions [Image: description], [Table: what to show]
11. Demonstrates E-E-A-T (Experience, Expertise, Authority, Trust)
12. Is optimized for both traditional SEO and AI search (LLMs)

🚨 CRITICAL SEO REQUIREMENTS:
- **Primary Keyword**: Include '{keywords[0] if keywords else 'N/A'}' in:
  * Article title
  * Meta title
  * Meta description
  * First paragraph (within first 100 words)
  * At least 2 H2 headers
  * Image alt text (at least 1 image)
- **Internal Links**: Include at least 3-5 internal links with descriptive anchor text (NO "click here")
- **NO External Links**: Do NOT create external links - AI cannot verify URLs are real
- **Images**: When creating [Image: description] placeholders, make descriptions keyword-rich and detailed
- **Text Emphasis**: Use <strong> for important keywords, <em> for emphasis
- **Lists**: Include multiple bullet points (ul) and numbered lists (ol) for readability

ARTICLE STRUCTURE:
- Engaging introduction (hook the reader immediately)
- 6-10 main sections with descriptive H2 headers (MORE comprehensive than competitors)
- Subsections with H3 headers for deep coverage
- Bullet points, numbered lists, and comparison tables for clarity
- FAQ section answering common questions (great for featured snippets!)
- Strong conclusion with actionable next steps

LENGTH: 2500-4000 words (be COMPREHENSIVE to outrank competitors)

META DATA & TAXONOMIES:
- Create a NEW, SEO-optimized title (under 60 chars, include primary keyword, must be different from old title)
- Meta Title: Similar to title but optimized for SERP click-through
- Meta Description: Compelling 150-155 char description that drives clicks
- Categories: 3-5 relevant, broad categories (e.g., "Photography Tips", "Camera Reviews")
- Tags: 5-8 specific, relevant tags (e.g., "astrophotography", "ZWO cameras", "planetary imaging")
  * Tags should be highly specific to the content
  * Include product names, techniques, or specific topics mentioned
  * Help users discover related content

SCHEMA MARKUP (JSON-LD):
Generate appropriate schema.org structured data for this content:
- **Article schema** (ALWAYS include): datePublished, headline, author, image, publisher
- **FAQ schema** (if content has Q&A sections): Include questions and answers
- **HowTo schema** (if step-by-step instructions): Include steps with details
- **Product/Review schema** (if reviewing products): Include ratings, products

OUTPUT FORMAT:
Return ONLY valid JSON:
{{
  "title": "SEO-optimized title here",
  "content": "Full HTML article content here",
  "categories": ["cat1", "cat2"],
  "tags": ["tag1", "tag2", "tag3"],
  "meta_title": "SEO title under 60 chars",
  "meta_description": "Meta description under 155 chars",
  "schema_markup": {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Article headline",
    "datePublished": "{current_date.isoformat()}",
    "author": {{"@type": "Organization", "name": "Site Name"}},
    "publisher": {{"@type": "Organization", "name": "Site Name"}}
  }}
}}

CRITICAL JSON REQUIREMENTS:
- All quotes inside strings MUST be escaped with backslash: \\"
- All newlines inside strings MUST be escaped: \\n
- All backslashes MUST be escaped: \\\\
- The JSON must be valid and parseable
- If content contains HTML with quotes, they must be properly escaped
- Example: "content": "This is a quote: \\"Hello\\" and this is HTML: <p>Text</p>"

DO NOT include any text outside the JSON structure."""

        # Increase max_tokens for complex content (recipes, lists, etc.)
        # Balanced for quality vs Vercel timeout constraints
        message = self.client.messages.create(
            model=self.model,
            max_tokens=12000,  # Balanced: enough for ~15 recipes while avoiding timeouts
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        import json
        response_text = message.content[0].text.strip()
        # Remove markdown code blocks if present
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        
        # Try to parse JSON with better error handling
        try:
            article_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing error: {e}")
            print(f"⚠️  Response text preview (first 500 chars): {response_text[:500]}")
            
            # Try to fix common JSON issues
            # 1. Try to find and extract JSON from the response
            import re
            # Look for JSON object boundaries
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    response_text = json_match.group(0)
                    article_data = json.loads(response_text)
                    print(f"✅ Successfully extracted JSON from response")
                except:
                    pass
            
            # 2. Try to fix unescaped quotes in strings
            if 'article_data' not in locals():
                try:
                    # Replace unescaped newlines in strings
                    fixed_json = re.sub(r'(?<!\\)"(.*?)(?<!\\)"', lambda m: '"' + m.group(1).replace('\n', '\\n').replace('\r', '\\r') + '"', response_text)
                    article_data = json.loads(fixed_json)
                    print(f"✅ Fixed JSON by escaping newlines")
                except:
                    pass
            
            # 3. If still failing, try to manually extract content
            if 'article_data' not in locals():
                print(f"❌ Failed to parse JSON. Attempting manual extraction...")
                # Try to extract fields manually using regex
                article_data = {}
                
                # Extract title
                title_match = re.search(r'"title"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response_text)
                if title_match:
                    article_data['title'] = title_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                
                # Extract content (may span multiple lines)
                content_match = re.search(r'"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response_text, re.DOTALL)
                if not content_match:
                    # Try alternative pattern for multi-line content
                    content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.|\\n)*)"', response_text, re.DOTALL)
                if content_match:
                    article_data['content'] = content_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
                
                # Extract other fields
                for field in ['categories', 'tags', 'meta_title', 'meta_description']:
                    field_match = re.search(f'"{field}"\\s*:\\s*"([^"]*(?:\\\\.[^"]*)*)"', response_text)
                    if not field_match:
                        # Try array format for categories/tags
                        if field in ['categories', 'tags']:
                            array_match = re.search(f'"{field}"\\s*:\\s*\\[([^\\]]+)\\]', response_text)
                            if array_match:
                                items = [item.strip().strip('"') for item in array_match.group(1).split(',')]
                                article_data[field] = items
                    else:
                        article_data[field] = field_match.group(1).replace('\\"', '"')
                
                # Set defaults if missing
                article_data.setdefault('title', 'Untitled Article')
                article_data.setdefault('content', '')
                article_data.setdefault('categories', [])
                article_data.setdefault('tags', [])
                article_data.setdefault('meta_title', article_data.get('title', ''))
                article_data.setdefault('meta_description', '')
                
                print(f"⚠️  Manually extracted fields: {list(article_data.keys())}")
                
                if not article_data.get('content'):
                    raise ValueError("Could not extract content from Claude response. JSON parsing failed and manual extraction found no content.")

        # QUALITY VALIDATION
        self._validate_content_quality(article_data)

        # INJECT SCHEMA MARKUP into content
        if 'schema_markup' in article_data and article_data['schema_markup']:
            schema_json = article_data['schema_markup']
            schema_script = f'\n<script type="application/ld+json">\n{json.dumps(schema_json, indent=2)}\n</script>\n'

            # Append schema to end of content
            article_data['content'] += schema_script
            print(f"✅ Schema markup injected: {schema_json.get('@type', 'Unknown')}")

        # PROCESS TABLE PLACEHOLDERS - Replace [Table: description] with actual HTML tables
        if '[Table:' in article_data.get('content', ''):
            print(f"  📊 Processing table placeholders...")
            article_data['content'], table_info = self.replace_table_placeholders(
                article_data['content'],
                topic_title,
                keywords,
                research
            )
            if table_info:
                print(f"  ✅ Generated {len(table_info)} tables")

        return article_data

    def _validate_content_quality(self, article_data: Dict) -> None:
        """
        Validate generated content meets quality standards.

        Raises:
            ValueError: If content fails quality checks
        """
        content = article_data.get('content', '')
        title = article_data.get('title', '')

        # Check 1: Minimum word count
        word_count = len(content.split())
        if word_count < 1500:
            raise ValueError(f"Content too short: {word_count} words (minimum: 1500)")

        # Check 2: Detect AI disclosure language
        ai_patterns = [
            "as an ai",
            "i cannot",
            "i don't have access",
            "i am an ai",
            "as a language model"
        ]
        content_lower = content.lower()
        for pattern in ai_patterns:
            if pattern in content_lower:
                raise ValueError(f"Content contains AI disclosure: '{pattern}' - regenerate required")

        # Check 3: Ensure title exists and is reasonable length
        if not title or len(title) < 10:
            raise ValueError("Title missing or too short")

        if len(title) > 70:
            print(f"⚠️  Warning: Title may be too long ({len(title)} chars): {title}")

        # Check 4: Ensure content has HTML structure
        if '<h2' not in content and '<h3' not in content:
            raise ValueError("Content lacks proper HTML heading structure (no H2/H3 tags)")

        # Check 5: Check for categories and tags
        categories = article_data.get('categories', [])
        tags = article_data.get('tags', [])

        if len(categories) < 2:
            print(f"⚠️  Warning: Only {len(categories)} categories (recommended: 3-5)")

        if len(tags) < 4:
            print(f"⚠️  Warning: Only {len(tags)} tags (recommended: 5-8)")

        # Passed all checks
        print(f"✅ Content quality validated: {word_count} words, {len(categories)} categories, {len(tags)} tags")
    
    def analyze_competitor_content(self, topic: str, top_urls: List[str]) -> str:
        """Analyze top-ranking competitor content using web search."""
        urls_text = "\n".join([f"- {url}" for url in top_urls[:3]])

        prompt = f"""IMPORTANT: Use web search to fetch and analyze these competitor URLs.

Analyze the top-ranking content for "{topic}".

TOP RANKING URLs TO SEARCH AND ANALYZE:
{urls_text}

**Search the web** to access each of these URLs and analyze their content. Provide:

1. **Content structure and length** - How are the top articles organized? Typical word count?
2. **Key topics covered** - What subtopics do ALL top articles include?
3. **Content depth** - How detailed are they? Surface-level or comprehensive?
4. **Multimedia elements** - Images, videos, infographics, charts?
5. **Unique angles** - What makes each stand out? What gaps exist?
6. **Content formats** - Lists, how-to guides, comparisons, reviews?

**Critical: Actually search and analyze the actual URLs provided above.**

Be specific and actionable. Cite examples from the URLs."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            thinking={
                "type": "enabled",
                "budget_tokens": 1000
            }
        )

        # Extract text from response (handle thinking blocks)
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text

        return response_text
    
    def rate_limit_delay(self, delay_seconds: float = 1.0):
        """Add delay between API calls to respect rate limits."""
        time.sleep(delay_seconds)
    
    def extract_table_placeholders(self, content: str) -> List[Dict[str, str]]:
        """
        Extract all [Table: description] placeholders from content.
        
        Args:
            content: HTML content with table placeholders
            
        Returns:
            List of dicts with 'placeholder', 'description', and 'position'
        """
        pattern = r'\[Table:\s*([^\]]+)\]'
        matches = []
        
        for match in re.finditer(pattern, content):
            matches.append({
                'placeholder': match.group(0),
                'description': match.group(1).strip(),
                'position': match.start()
            })
        
        return matches
    
    def generate_table(self, description: str, article_title: str, keywords: List[str], research: str = None) -> str:
        """
        Generate an HTML table based on description using Claude.
        
        Args:
            description: Table description from placeholder (e.g., "Comparison of top 5 AI tools")
            article_title: Article title for context
            keywords: Article keywords for context
            research: Research data for generating accurate table content
            
        Returns:
            HTML table string or empty string if generation fails
        """
        try:
            print(f"  📊 Generating table: {description[:60]}...")
            
            # Build context for table generation
            context = f"Article: {article_title}\n"
            if keywords:
                context += f"Keywords: {', '.join(keywords)}\n"
            if research:
                # Include relevant research context (limit to avoid token limits)
                research_summary = research[:1000] if len(research) > 1000 else research
                context += f"\nResearch Context:\n{research_summary}\n"
            
            prompt = f"""You are creating an HTML table for a blog article.

CONTEXT:
{context}

TABLE REQUEST:
Create a professional, well-structured HTML table based on this description: "{description}"

REQUIREMENTS:
1. Generate COMPLETE, ACCURATE data based on the description - use web search if needed for current information
2. Create a well-formatted HTML table with proper structure
3. Include a descriptive caption
4. Use semantic HTML: <table>, <thead>, <tbody>, <tr>, <th>, <td>
5. Make it visually appealing with appropriate structure
6. Ensure data is accurate and current (use web search if needed)
7. Include all relevant columns/rows based on the description
8. Make the table responsive and accessible

EXAMPLE OUTPUT FORMAT:
<table>
<caption>Table Caption Here</caption>
<thead>
<tr>
<th>Column 1</th>
<th>Column 2</th>
<th>Column 3</th>
</tr>
</thead>
<tbody>
<tr>
<td>Data 1</td>
<td>Data 2</td>
<td>Data 3</td>
</tr>
</tbody>
</table>

IMPORTANT:
- Return ONLY the HTML table code (no markdown, no explanations, no ```html blocks)
- Do NOT include any text before or after the table
- Make sure the table data is comprehensive and accurate
- Use web search if needed to get current, accurate information
- Include enough rows/columns to make the table valuable

Generate the table now:"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract HTML table from response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text
            
            # Clean up the response - remove markdown code blocks if present
            response_text = response_text.strip()
            response_text = re.sub(r'^```html\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            # Validate it's actually HTML table
            if '<table' in response_text.lower() and '</table>' in response_text.lower():
                print(f"  ✅ Table generated successfully")
                return response_text
            else:
                print(f"  ⚠️  Generated content doesn't appear to be a valid HTML table")
                # Try to wrap it in table tags if it looks like table data
                if '<tr' in response_text or '<td' in response_text:
                    # Assume it's table content without outer tags
                    response_text = f"<table>{response_text}</table>"
                    return response_text
                return ""
                
        except Exception as e:
            print(f"  ⚠️  Error generating table: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def replace_table_placeholders(
        self,
        content: str,
        article_title: str,
        keywords: List[str],
        research: str = None
    ) -> tuple:
        """
        Replace [Table: description] placeholders with actual generated HTML tables.
        
        Args:
            content: HTML content with table placeholders
            article_title: Article title for context
            keywords: Article keywords for context
            research: Research data for generating accurate tables
            
        Returns:
            Tuple of (updated_content, list_of_table_info)
        """
        placeholders = self.extract_table_placeholders(content)
        
        if not placeholders:
            return content, []
        
        print(f"  📊 Found {len(placeholders)} table placeholders to generate")
        
        table_info_list = []
        replacements = []
        
        for i, placeholder_info in enumerate(placeholders):
            description = placeholder_info['description']
            
            print(f"  📊 Generating table {i+1}/{len(placeholders)}: {description[:50]}...")
            
            # Generate table HTML
            table_html = self.generate_table(description, article_title, keywords, research)
            
            if table_html:
                # Replace placeholder with generated table
                replacements.append((placeholder_info['placeholder'], table_html))
                
                table_info_list.append({
                    'description': description,
                    'html_length': len(table_html)
                })
                
                print(f"  ✅ Table generated and inserted")
            else:
                # If generation fails, leave placeholder as-is or add a comment
                print(f"  ⚠️  Failed to generate table for: {description}")
                # Option: Keep placeholder so user knows table was intended
                # Option: Remove placeholder entirely
                replacements.append((placeholder_info['placeholder'], f'<!-- Table generation failed: {description} -->'))
        
        # Replace all placeholders in reverse order (to preserve positions)
        updated_content = content
        for placeholder, table_html in replacements:
            updated_content = updated_content.replace(placeholder, table_html, 1)
        
        return updated_content, table_info_list