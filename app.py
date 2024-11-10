from flask import Flask, render_template, request, jsonify, send_file
import openai
from gtts import gTTS
from io import BytesIO
import os
import spacy

app = Flask(__name__)

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text')
    input_language = data.get('input_language', 'en-US')
    output_language = data.get('output_language', 'en')

    # Step 1: Correct medical terminology using GPT
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
            max_tokens=500,
            temperature=0.7
        )
        corrected_text = correction_response.choices[0].text.strip()

        # Step 2: Translate corrected text using GPT
        translation_prompt = f"""
        Translate the following text from {input_language} to {output_language} with a focus on medical terminology. Text: {corrected_text}
        """
        translation_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=translation_prompt,
            max_tokens=1000,
            temperature=0.7
        )
        translated_text = translation_response.choices[0].text.strip()

        # Step 3: Verify translation accuracy
        verification_prompt = f"""
        You are a translation verification AI that checks the relevance and quality of translations, 
        especially for medical terminology. Evaluate if the following translated text accurately 
        reflects the input text and conforms to the {output_language} language and dialect.

        Input Text: {corrected_text}
        Translated Text: {translated_text}
        Input Language: {input_language}
        Output Language: {output_language}

        Please respond with 'Accurate' if the translation is accurate, or provide suggestions for improvement.
        """
        verification_response = openai.Completion.create(
            model="gpt-3.5-turbo-instruct",
            prompt=verification_prompt,
            max_tokens=50,
            temperature=0.5
        )
        verification_result = verification_response.choices[0].text.strip()

        # Compile results for response
        response_data = {
            'corrected_text': corrected_text,
            'translated_text': translated_text,
            'verification': verification_result
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
