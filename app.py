from flask import Flask, render_template, request, jsonify, send_file
import openai
from gtts import gTTS
from io import BytesIO
import os
import random
from datetime import datetime

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Generate a token for every session, updating every minute
def generate_token():
    return random.randint(1, 100)

# Global variable to store the current token
current_token = generate_token()

@app.route('/')
def index():
    global current_token
    # Update token every minute
    current_token = generate_token()
    return render_template('index.html', token=current_token)

@app.route('/verify-token', methods=['POST'])
def verify_token():
    global current_token
    data = request.get_json()
    user_token = data.get('token')

    # Check if token matches the current one
    if user_token != str(current_token):
        return jsonify({'error': 'Invalid token. Please check the token and try again.'}), 403

    return jsonify({'message': 'Token verified successfully'})

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Step 1: Confidentiality check for prototype
    confidentiality_notice = "Sensitive data processing is restricted to internal operations for confidentiality."
    print(confidentiality_notice)  # Logging for demonstration purposes

    # Step 2: Correct potential mispronunciations or errors in the medical terms
    correction_prompt = f"""
    You are a medical language expert AI that accurately understands medical terminology.
    The user may have mispronounced or mistyped some medical terms. Please help to interpret 
    and correct any potential errors in medical terms within the following input:
    Text: {text}
    
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

    # Step 3: Translate the corrected text
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

    # Step 4: Verify and adjust translation accuracy
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

    return jsonify({
        'corrected_text': corrected_text,
        'translated_text': final_translated_text
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
