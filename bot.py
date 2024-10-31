import os
import google.generativeai as genai
from google.colab import userdata

import IPython.display as ipd
from googletrans import Translator
from langdetect import detect
import iso639
import speech_recognition as sr

# Define language families and their corresponding language codes
LANGUAGE_FAMILIES = {
    'Kenyan': ['sw', 'ki', 'luo', 'kam', 'kln', 'guz', 'mer', 'luy', 'mas', 'tuv', 'saq', 'dav', 'pkm', 'rel', 'bor'],
    'International': ['en', 'fr', 'es', 'de', 'pt', 'it'],
    'Asian': ['zh-cn', 'ja', 'ko', 'hi', 'ar']
}

# Flatten LANGUAGE_FAMILIES for easy lookup
SUPPORTED_LANGUAGES = [code for codes in LANGUAGE_FAMILIES.values() for code in codes]

# Define culturally appropriate phrases for different languages
KENYAN_PHRASES = {
    'sw': {
        'welcome': 'Karibu! Naweza kukusaidia vipi?',
        'goodbye': 'Kwaheri! Tutaonana tena!',
        'choose_format': 'Chagua muundo: 1 kwa maandishi, 2 kwa sauti'
    },
    'ki': {
        'welcome': 'Nĩ wega mũno! Ndĩ ngũteithia atĩa?',
        'goodbye': 'Nĩ wega! Tũgũcemania rĩngĩ!',
        'choose_format': 'Thuura njira: 1 kwa wandiki, 2 kwa mũgambo'
    },
    # Add more languages as needed
}

class ChatMode:
    TEXT = "text"
    VOICE = "voice"

class MultilingualChatbot:
    def __init__(self):
        self.translator = Translator()
        self.recognizer = sr.Recognizer()
        self.chat_mode = None
        self.preferred_lang = None

    def setup_genai(self):
        """Setup Google's Generative AI with API key"""
        try:
            genai.configure(api_key=userdata.get('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel('gemini-pro')
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            print(f"Error setting up Gemini: {e}")
            raise

    def get_chat_mode(self):
        """Let user choose between text and voice mode"""
        while True:
            if self.preferred_lang in KENYAN_PHRASES:
                prompt = KENYAN_PHRASES[self.preferred_lang]['choose_format']
            else:
                prompt = translate_text("Choose format: 1 for text, 2 for voice", self.preferred_lang)

            print(f"\n{prompt}")
            choice = input().strip()

            if choice == '1':
                return ChatMode.TEXT
            elif choice == '2':
                return ChatMode.VOICE
            else:
                print("Invalid choice. Please enter 1 or 2.")

    def voice_to_text(self):
        """Convert voice input to text"""
        try:
            with sr.Microphone() as source:
                print("\nListening...")
                audio = self.recognizer.listen(source, timeout=5)

            # Use appropriate language model based on preferred language
            if self.preferred_lang == 'en':
                text = self.recognizer.recognize_google(audio, language='en-US')
            else:
                # Map language codes to Google Speech Recognition language codes
                lang_code = {
                    'sw': 'sw-KE',
                    'ki': 'en-KE',  # Fallback to Kenyan English
                    'fr': 'fr-FR',
                    'es': 'es-ES',
                    # Add more language mappings as needed
                }.get(self.preferred_lang, 'en-US')

                text = self.recognizer.recognize_google(audio, language=lang_code)
            return text
        except sr.RequestError:
            print("Could not request results from speech recognition service")
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except Exception as e:
            print(f"Error in voice recognition: {e}")
            return None

    def text_to_speech(self, text, lang_code):
        """Convert text to speech and play it"""
        try:
            # Map custom language codes to compatible gTTS codes
            tts_lang_map = {
                'sw': 'sw',
                'ki': 'en',  # Fallback to English for unsupported languages
                'luo': 'en',
                'kam': 'en',
                'zh-cn': 'zh-CN'
            }

            tts_lang = tts_lang_map.get(lang_code, lang_code)
            tts = gTTS(text=text, lang=tts_lang)
            tts.save("output.mp3")
            ipd.display(ipd.Audio("output.mp3", autoplay=True))
            os.remove("output.mp3")
        except Exception as e:
            print(f"Text-to-speech error: {str(e)}")

    def get_bot_response(self, user_input):
        """Get response from the chatbot"""
        try:
            # Translate user input to English for processing if not in English
            if self.preferred_lang != 'en':
                english_input = translate_text(user_input, 'en')
            else:
                english_input = user_input

            # Get response from Gemini
            response = self.chat.send_message(english_input)

            # Translate response back to preferred language if not English
            if self.preferred_lang != 'en':
                return translate_text(response.text, self.preferred_lang)
            return response.text

        except Exception as e:
            print(f"Error getting bot response: {e}")
            return translate_text("I'm sorry, I couldn't process that request.", self.preferred_lang)

    def run(self):
        """Main chat loop"""
        try:
            print("Karibu! Welcome to the Multilingual Chat System")

            # Display available languages
            self.display_languages()

            # Get user's preferred language
            self.preferred_lang = get_user_language_preference()

            # Get preferred chat mode
            self.chat_mode = self.get_chat_mode()

            # Setup Gemini chat
            self.setup_genai()

            # Display welcome message
            welcome_msg = KENYAN_PHRASES.get(self.preferred_lang, {}).get('welcome',
                         translate_text("Hello, how can I help you?", self.preferred_lang))
            print(f"\nBot: {welcome_msg}")
            if self.chat_mode == ChatMode.VOICE:
                self.text_to_speech(welcome_msg, self.preferred_lang)

            while True:
                # Get user input based on chosen mode
                if self.chat_mode == ChatMode.VOICE:
                    user_input = self.voice_to_text()
                    if user_input:
                        print(f"\nYou said: {user_input}")
                else:
                    user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    goodbye_msg = KENYAN_PHRASES.get(self.preferred_lang, {}).get('goodbye',
                                translate_text("Goodbye! Take care!", self.preferred_lang))
                    print(f"\nBot: {goodbye_msg}")
                    if self.chat_mode == ChatMode.VOICE:
                        self.text_to_speech(goodbye_msg, self.preferred_lang)
                    break

                # Get and display bot response
                response = self.get_bot_response(user_input)
                print(f"\nBot: {response}")
                if self.chat_mode == ChatMode.VOICE:
                    self.text_to_speech(response, self.preferred_lang)

        except Exception as e:
            print(f"Fatal error: {str(e)}")

    def display_languages(self):
        """Display available languages by family"""
        print("\nAvailable language families:")
        for family, codes in LANGUAGE_FAMILIES.items():
            print(f"\n{family} Languages:")
            for code in codes:
                lang_name = get_language_name(code)
                if family == 'Kenyan':
                    region = {
                        'ki': '(Central)',
                        'luo': '(Nyanza)',
                        'kam': '(Eastern)',
                        'kln': '(Rift Valley)',
                        'guz': '(Nyanza)',
                        'mer': '(Eastern)',
                        'luy': '(Western)',
                        'mas': '(Rift Valley)',
                        'tuv': '(Northern)',
                        'saq': '(Central)',
                        'dav': '(Coast)',
                        'pkm': '(Coast)',
                        'rel': '(Northern)',
                        'bor': '(Northern)'
                    }.get(code, '')
                    print(f"  - {lang_name} ({code}) {region}")
                else:
                    print(f"  - {lang_name} ({code})")

# Keep existing helper functions
def translate_text(text, target_lang):
    """Translate text to target language"""
    try:
        translator = Translator()
        if target_lang == 'zh-cn':
            target_lang = 'zh-CN'
        translation = translator.translate(text, dest=target_lang)
        return translation.text
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return text

def get_language_name(code):
    """Get full language name from code"""
    custom_language_names = {
        'sw': 'Swahili',
        'ki': 'Kikuyu',
        'luo': 'Luo',
        'kam': 'Kamba',
        'kln': 'Kalenjin',
        'guz': 'Kisii',
        'mer': 'Meru',
        'luy': 'Luhya',
        'mas': 'Maasai',
        'tuv': 'Turkana',
        'saq': 'Samburu',
        'dav': 'Taita',
        'pkm': 'Pokomo',
        'rel': 'Rendille',
        'bor': 'Borana'
    }

    if code in custom_language_names:
        return custom_language_names[code]

    try:
        if len(code) == 2:
            return iso639.languages.get(alpha2=code).name
        elif len(code) == 3:
            return iso639.languages.get(alpha3=code).name
        elif code == 'zh-cn':
            return 'Chinese (Simplified)'
        else:
            return code.upper()
    except (KeyError, AttributeError):
        return code.upper()

def get_user_language_preference():
    """Get user's preferred language"""
    while True:
        print("\nPlease enter your preferred language code (e.g., 'sw' for Swahili, 'en' for English):")
        lang_code = input().strip().lower()
        if lang_code in SUPPORTED_LANGUAGES:
            return lang_code
        else:
            print(f"Sorry, '{lang_code}' is not supported. Please choose from the available languages listed above.")

if __name__ == "__main__":
    chatbot = MultilingualChatbot()
    chatbot.run()
