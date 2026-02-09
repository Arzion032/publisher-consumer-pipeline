import os
import json
import logging
import google.generativeai as genai

# Google Gemini configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# AI analysis function
def analyze_article(title, content, max_content_chars=2000):
    
    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='[AI_ANALYSIS] %(asctime)s %(levelname)s: %(message)s',
    )
    logger = logging.getLogger(__name__)
    
    try:
        prompt = f"""
        You are an information extraction system.

        Your job is to analyze a news article and extract structured data.

        IMPORTANT RULES:
        - Output must be valid JSON
        - Do NOT include explanations or markdown
        - Do NOT include text before or after JSON
        - If unsure, make the best reasonable guess

        JSON SCHEMA:
        {{
        "summary": string,
        "sentiment": "positive" | "negative" | "neutral",
        "keywords": [string, string, string, string, string]
        }}

        INSTRUCTIONS:
        1. Summary must be exactly 2 sentences.
        2. Sentiment is based on the overall tone of the article:
           - positive → optimistic or beneficial developments
           - negative → harm, crime, conflict, danger, failure
           - neutral → factual reporting without emotional tone
        3. Keywords must be 5 important concrete terms from the article:
           organizations, technologies, locations, people, major concepts
           (single words or short phrases only)

        ARTICLE TITLE:
        {title}

        ARTICLE CONTENT:
        {content[:max_content_chars]}
        """
        response = model.generate_content(prompt)
        logger.info("✅ AI analysis successful for article: %s", title)
        
        return response.text

    except Exception as e:
        logger.error("❌AI ANALYSIS FAILED: %s", e)

        return json.dumps({
        "summary": None,
        "sentiment": None,
        "keywords": []
         })
