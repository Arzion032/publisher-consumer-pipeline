import os
import google.generativeai as genai

# Load Google API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# the gemini fastest model
model = genai.GenerativeModel("gemini-2.5-flash-lite")

def analyze_article(title, content):
    try:
        prompt = f"""
            You are an information extraction system.

            Your job is to analyze a news article and extract structured data.

            IMPORTANT RULES:
            - Output must be valid JSON
            - Do NOT include explanations
            - Do NOT include markdown
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
            - organizations
            - technologies
            - locations
            - people
            - major concepts
            (single words or short phrases only)

            ARTICLE TITLE:
            {title}

            ARTICLE CONTENT:
            {content[:2000]}
        """

        response = model.generate_content(prompt)

        return response.text
    
    except Exception as e:
        print("AI ANALYSIS FAILED:", e)

        # return a default response in case of failure
        import json
        return json.dumps({
            "summary": None,
            "sentiment": None,
            "keywords": []
        })