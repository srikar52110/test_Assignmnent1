from flask import Flask, render_template, request, jsonify, session
from cryptography.fernet import Fernet
import openai
from gtts import gTTS
from io import BytesIO
import os
import random
import time

app = Flask(__name__)

# Set up the Flask secret key (this is important for session management)
app.secret_key = os.urandom(24)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize encryption key
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# For the token number (for simplicity, we store it globally for this example)
token_number = None
token_timestamp = None

@app.route('/')
def index():
    global token_number, token_timestamp
    current_time = time.time()

    # Generate a new token every minute
    if not token_timestamp or current_time - token_timestamp >= 60:
        token_number = random.randint(1, 100)
        token_timestamp = current_time

    return render_template('index.html', token_number=token_number)

@app.route('/enter_token', methods=['POST'])
def enter_token():
    data = request.get_json()
    token_entered = data.get('token')

    if token_entered == str(token_number):
        session['token_verified'] = True
        return jsonify({'success': 'Token verified! You can now proceed.'})
    else:
        session['token_verified'] = False
        return jsonify({'error': 'Wrong token. Please try again.'}), 400

@app.route('/translate', methods=['POST'])
def translate():
    # Ensure that token verification is successful
    if not session.get('token_verified'):
        return jsonify({'error': 'Please verify token to proceed.'}), 403

    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Encrypt sensitive input data (for confidentiality)
    encrypted_text = cipher_suite.encrypt(text.encode())

    try:
        # Decrypt the data for processing
        decrypted_text = cipher_suite.decrypt(encrypted_text).decode()

        # Use OpenAI to translate the text (simplified)
        prompt = f"""
        Translate the following text from {input_language} to {output_language} with a focus on medical terminology. Text: {decrypted_text}
        """
        response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7
        )
        translated_text = response.choices[0].text.strip()

        # Encrypt the translated text before sending back (for confidentiality)
        encrypted_translated_text = cipher_suite.encrypt(translated_text.encode())
        
        return jsonify({'translated_text': encrypted_translated_text.decode()})
    except Exception as e:
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@app.route('/speak', methods=['POST'])
def speak():
    # Ensure that token verification is successful
    if not session.get('token_verified'):
        return jsonify({'error': 'Please verify token to proceed.'}), 403

    data = request.get_json()
    text = data.get('text')
    language = data.get('language', 'en')

    try:
        # Generate speech from the text in memory
        tts = gTTS(text=text, lang=language, slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)

        # Return audio stream directly without saving
        return send_file(audio_bytes, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
