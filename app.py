from flask import Flask, render_template, request, jsonify, send_file
import openai
from gtts import gTTS
from io import BytesIO
import os
from cryptography.fernet import Fernet

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Generate a secret key for encryption/decryption (For demonstration purposes)
secret_key = Fernet.generate_key()
cipher_suite = Fernet(secret_key)

# Store the current token (this can be set to any value, here it's for illustration purposes)
current_token = 42  # Example token, can be generated dynamically

@app.route('/')
def index():
    # Display the token to the user
    return render_template('index.html', token=current_token)

@app.route('/verify-token', methods=['POST'])
def verify_token():
    data = request.get_json()
    token = data.get('token', '')

    # Verify if the token entered by the user matches the one we generated
    if int(token) == current_token:
        return jsonify({"message": "Token verified successfully"})
    else:
        return jsonify({"error": "Invalid token"})

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Encrypt the text before sending to OpenAI for translation
    encrypted_text = cipher_suite.encrypt(text.encode()).decode()

    # Display a message showing that the text is being encrypted
    encryption_message = "Your message is being encrypted for confidentiality."

    # Step 1: Correct potential mispronunciations or errors in the medical terms
    correction_prompt = f"""
    You are a medical language expert AI that accurately understands medical terminology.
    The user may have mispronounced or mistyped some medical terms. Please help to interpret 
    and correct any potential errors in medical terms within the following input:
    Text: {encrypted_text}
    
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
        
        # Decrypt the corrected text after processing
        decrypted_corrected_text = cipher_suite.decrypt(corrected_text.encode()).decode()
    except Exception as e:
        return jsonify({'error': f'Correction step failed: {str(e)}'}), 500

    # Step 2: Translate the corrected text
    translation_prompt = f"""
    Translate the following text from {input_language} to {output_language} with a focus on medical terminology. Text: {decrypted_corrected_text}
    """
    try:
        translation_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=translation_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        translated_text = translation_response.choices[0].text.strip()

        # Decrypt the translated text after translation
        decrypted_translated_text = cipher_suite.decrypt(translated_text.encode()).decode()
    except Exception as e:
        return jsonify({'error': f'Translation step failed: {str(e)}'}), 500

    # Step 3: Verify and adjust translation accuracy
    verification_prompt = f"""
    You are a medical language expert AI specializing in translation accuracy for medical terminology.
    Please review the translated text and make any necessary adjustments to ensure it accurately 
    reflects the original meaning, particularly for complex or sensitive medical terms. If the 
    translation does not fully convey the intent or specific medical terms of the input, modify it 
    accordingly.

    Original Text: {decrypted_corrected_text}
    Initial Translated Text: {decrypted_translated_text}
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

        # Decrypt the final translated text
        final_translated_text_decrypted = cipher_suite.decrypt(final_translated_text.encode()).decode()
    except Exception as e:
        return jsonify({'error': f'Verification step failed: {str(e)}'}), 500

    return jsonify({
        'encryption_message': encryption_message,
        'corrected_text': decrypted_corrected_text,
        'translated_text': final_translated_text_decrypted
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
