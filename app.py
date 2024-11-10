from flask import Flask, render_template, request, jsonify, send_file
from cryptography.fernet import Fernet
import openai
from gtts import gTTS
from io import BytesIO
import os
import random
import time

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Generate a new encryption key for Fernet
# You would normally store this in a secure location
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# Store the token value (it will be updated every minute)
current_token = None
token_timestamp = None

# Generate a new token every minute
def generate_token():
    global current_token, token_timestamp
    current_token = random.randint(1, 100)
    token_timestamp = time.time()

@app.route('/')
def index():
    generate_token()  # Generate the token at the start
    return render_template('index.html', token=current_token)

# Endpoint to verify token
@app.route('/verify_token', methods=['POST'])
def verify_token():
    data = request.get_json()
    token = data.get('token')
    
    # Check if the token is correct and has not expired
    if token == current_token and (time.time() - token_timestamp) < 60:
        return jsonify({'message': 'Token verified'})
    else:
        return jsonify({'message': 'Invalid or expired token'}), 400
        
# Endpoint for translation
@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    encrypted_text = data.get('text')
    
    # Decrypt the text
    try:
        decrypted_text = cipher_suite.decrypt(encrypted_text.encode()).decode()
    except Exception as e:
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500

    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Step 1: Correct potential mispronunciations or errors in the medical terms
    correction_prompt = f"""
    You are a medical language expert AI that accurately understands medical terminology.
    The user may have mispronounced or mistyped some medical terms. Please help to interpret 
    and correct any potential errors in medical terms within the following input:
    Text: {decrypted_text}
    
    Ensure that the text is corrected in {input_language} language for optimal translation accuracy.
    """
    try:
        correction_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=correction_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        corrected_text = correction_response.choices[0].text.strip()
    except Exception as e:
        return jsonify({'error': f'Correction step failed: {str(e)}'}), 500

    # Step 2: Translate the corrected text
    translation_prompt = f"""
    Translate the following text from {input_language} to {output_language} with a focus on medical terminology. Text: {corrected_text}
    """
    try:
        translation_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=translation_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        translated_text = translation_response.choices[0].text.strip()
    except Exception as e:
        return jsonify({'error': f'Translation step failed: {str(e)}'}), 500

    # Step 3: Verify and adjust translation accuracy
    verification_prompt = f"""
    You are a medical language expert AI specializing in translation accuracy for medical terminology.
    Please review the translated text and make any necessary adjustments to ensure it accurately 
    reflects the original meaning, particularly for complex or sensitive medical terms. If the 
    translation does not fully convey the intent or specific medical terms of the input, modify it 
    accordingly.

    Original Text: {corrected_text}
    Initial Translated Text: {translated_text}
    Input Language: {input_language}
    Output Language: {output_language}

    Provide the finalized translation that most accurately preserves the meaning and context.
    """
    try:
        verification_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=verification_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        final_translated_text = verification_response.choices[0].text.strip()
    except Exception as e:
        return jsonify({'error': f'Verification step failed: {str(e)}'}), 500

    # Encrypt the translated text
    encrypted_translated_text = cipher_suite.encrypt(final_translated_text.encode()).decode()

    return jsonify({
        'corrected_text': corrected_text,
        'encrypted_translated_text': encrypted_translated_text
    })

# Endpoint for text-to-speech conversion
@app.route('/speak', methods=['POST'])
def speak():
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
