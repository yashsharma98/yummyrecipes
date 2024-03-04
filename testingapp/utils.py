import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

def summarize_text(text):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=text,
            max_tokens=150,  # Adjust as needed
            temperature=0.4,  # Adjust as needed
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error in text summarization: {e}")
        return text  # Return original text on error