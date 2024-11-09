from flask import Flask, render_template, request, jsonify
import openai
import os

# Initialize Flask app
app = Flask(__name__)

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/')
def index():
    return render_template('index.html')  # This renders index.html from templates/

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Use OpenAI to translate the text
    prompt = f"""
You are a helpful AI that translates text with medical accuracy. Text: {text}
Translate it from {input_language} to {output_language}.
"""
    
    try:
        # Call OpenAI API to perform translation
        response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        translated_text = response.choices[0].text.strip()
        return jsonify({'translated_text': translated_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
