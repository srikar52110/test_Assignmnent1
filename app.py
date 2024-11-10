from flask import Flask, render_template, request, jsonify, send_file
import openai
from gtts import gTTS
from io import BytesIO
import os
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64encode, b64decode
import time

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Global token to be generated and updated every minute
token = random.randint(1, 100)

# Secret key for encryption/decryption
SECRET_KEY = os.urandom(16)  # AES key (16 bytes)

@app.route('/')
def index():
    # Return the token to be displayed on the UI
    return render_template('index.html', token=token)

@app.route('/verify-token', methods=['POST'])
def verify_token():
    global token
    data = request.get_json()
    entered_token = int(data.get('token'))

    # Validate token
    if entered_token == token:
        return jsonify({'message': 'Token verified successfully! You can now proceed.'})
    else:
        return jsonify({'error': 'Invalid token. Please try again.'})

@app.route('/update-token', methods=['GET'])
def update_token():
    global token
    token = random.randint(1, 100)  # Update token every minute
    return jsonify({'token': token})

# Function to encrypt text
def encrypt_text(text):
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(text.encode(), AES.block_size))
    iv = b64encode(cipher.iv).decode('utf-8')
    ct = b64encode(ct_bytes).decode('utf-8')
    return iv, ct

# Function to decrypt text
def decrypt_text(iv, ct):
    iv = b64decode(iv)
    ct = b64decode(ct)
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Step 1: Encrypt the input text
    iv, encrypted_text = encrypt_text(text)
    encrypted_message = "Your message is being encrypted..."

    # Step 2: Decrypt the input text (simulate)
    decrypted_text = decrypt_text(iv, encrypted_text)
    encryption_decryption_message = "Your message is being decrypted..."

    # Step 3: Correct potential mispronunciations or errors in medical terms
    correction_prompt = f"""
    You are a medical language expert AI that accurately understands medical terminology.
    The user may have mispronounced or mistyped some medical terms. Please help to interpret 
    and correct any potential errors in medical terms within the following input:
    Text: {decrypted_text}
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

    # Step 3: Encrypt the translated text
    iv, encrypted_translated_text = encrypt_text(translated_text)
    output_encryption_message = "Your translated message is being encrypted..."

    # Step 4: Decrypt the translated text (simulate)
    decrypted_translated_text = decrypt_text(iv, encrypted_translated_text)
    decryption_message = "Your translated message is being decrypted..."

    return jsonify({
        'corrected_text': corrected_text,
        'translated_text': decrypted_translated_text,
        'encryption_message': encrypted_message,
        'decryption_message': encryption_decryption_message,
        'output_encryption_message': output_encryption_message,
        'decryption_message': decryption_message
    })

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
