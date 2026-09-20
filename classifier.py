import json
import re
import google.generativeai as genai
from config import Config

def classify_emails(email_list):
    """
    Classifies a list of emails into 'Business' and 'Individual' using Gemini API.
    Fallback to domain regex if API fails.
    """
    if Config.GEMINI_API_KEY:
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = (
                "You are an email classification assistant. Categorize the following emails strictly into two categories: "
                "'Business' (corporate, custom domains like hr@tcs.com, contact@startup.io) and "
                "'Individual' (generic/free providers like @gmail.com, @yahoo.com, @outlook.com, @hotmail.com).\n"
                "Return ONLY a valid JSON object in this exact format, with no other text:\n"
                '{"Business": ["email1", ...], "Individual": ["email2", ...]}\n\n'
                f"Emails to classify: {json.dumps(email_list)}"
            )
            
            response = model.generate_content(prompt)
            text_response = response.text.strip()
            
            # Clean markdown formatting if present
            if text_response.startswith('```json'):
                text_response = text_response[7:]
            if text_response.startswith('```'):
                text_response = text_response[3:]
            if text_response.endswith('```'):
                text_response = text_response[:-3]
            
            return json.loads(text_response.strip())
        except Exception as e:
            print(f"Gemini API classification failed: {e}. Falling back to regex.")
            return _regex_classify(email_list)
    else:
        print("No Gemini API Key found. Falling back to regex.")
        return _regex_classify(email_list)

def _regex_classify(email_list):
    generic_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'aol.com', 'icloud.com']
    result = {"Business": [], "Individual": []}
    
    for email in email_list:
        try:
            domain = email.split('@')[1].lower()
            if domain in generic_domains:
                result["Individual"].append(email)
            else:
                result["Business"].append(email)
        except IndexError:
            # Invalid email format, skip or default to individual
            continue
            
    return result
