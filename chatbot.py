from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini API - API key directly in code (for development only)
GOOGLE_API_KEY = "AIzaSyArihOGcyK5KcQR4ntIqNga6bSoq7kM7Yo"  # Replace with your actual key

try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Failed to configure Gemini API: {str(e)}")
    raise


# Set up the model
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# Medical system prompt
MEDICAL_PROMPT = """
You are Sister Andy  , a professional medical assistant chatbot. Your role is to:

1. Provide general health information and answer medical questions
2. Explain medical terms in simple language
3. Offer guidance on symptoms and common conditions
4. Suggest when to seek professional medical help
5. Provide basic first aid information

IMPORTANT RULES:
- Always clarify that you are not a substitute for professional medical advice
- Never diagnose specific conditions - suggest possibilities only
- For emergencies, always advise to contact local emergency services
- Be empathetic and understanding in all responses
- Keep responses clear and concise (1-3 paragraphs max)
- Ask follow-up questions when more information would help provide better guidance

Current conversation:
"""

chat = model.start_chat(history=[])
chat.send_message(MEDICAL_PROMPT)

@app.route('/')
def home():
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat_handler():
    user_message = request.json['message']
    
    try:
        # Get response from Gemini
        response = chat.send_message(user_message)
        bot_response = response.text
        
        return jsonify({
            'status': 'success',
            'response': bot_response
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'response': f"Sorry, I encountered an error: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=True)