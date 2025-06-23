import streamlit as st
import pdfplumber
import google.generativeai as genai
import edge_tts
import re
import tempfile
import asyncio

# Configurations
GOOGLE_API_KEY = 'AIzaSyABjfe6yTuzJXrMJyjFmiGYshld81TPS3k'
genai.configure(api_key=GOOGLE_API_KEY)

# Voice settings
VOICES = {
    'Alex': ('en-US-ChristopherNeural', '+15%'),
    'Samantha': ('en-US-JennyNeural', '+15%')
}

# Helper functions
def remove_timestamps(text):
    """Remove [hh:mm:ss] or [mm:ss] timestamps from text."""
    return re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', '', text)

def parse_conversation(conversation_text):
    """Parse conversation text and extract speaker segments for TTS"""
    segments = []
    speaker_regex = re.compile(r'^(Alex|Samantha):\s*(.*)', re.IGNORECASE)
    lines = conversation_text.split('\n')
    current_speaker = None
    current_text = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = speaker_regex.match(line)
        if match:
            if current_speaker and current_text:
                segments.append((current_speaker, current_text.strip()))
            current_speaker = match.group(1).capitalize()
            current_text = match.group(2).strip()
        else:
            if current_speaker:
                current_text += " " + line
    if current_speaker and current_text:
        segments.append((current_speaker, current_text.strip()))
    return segments

def convert_to_conversation(text_content):
    prompt = f"""
    You are an expert science communicator and podcast host. Convert the following research paper 
    into an engaging podcast-style conversation between two hosts (let's call them Alex and Samantha). 
    
    The conversation should:
    1. Be natural and conversational, like a real podcast
    2. Break down complex concepts into easily understandable terms
    3. Include questions, clarifications, and examples
    4. Maintain the key insights and findings from the research
    5. Be engaging and accessible to a general audience
    6. Include timestamps or sections for better organization
    
    Format the output as a conversation with clear speaker labels.
    Every line of dialogue must start with either "Alex:" or "Samantha:" (case-sensitive, with a colon and a space).
    Do not use any other speaker labels or formatting.
    
    Research Paper Content:
    {text_content}
    
    Please create a podcast conversation that makes this research accessible and interesting.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

async def convert_to_audio(conversation_text):
    conversation_text = remove_timestamps(conversation_text)
    segments = parse_conversation(conversation_text)
    audio_segments = []
    for i, (speaker, text) in enumerate(segments):
        if not text.strip():
            continue
        voice, rate = VOICES[speaker]
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio_data = b''
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        audio_segments.append(audio_data)
    if audio_segments:
        return b''.join(audio_segments)
    else:
        return None

# Streamlit UI
st.title("PDF to Podcast")
st.write("Upload a PDF, and get a podcast-style conversation with audio!")

uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_pdf_path = tmp_file.name
    st.success("PDF uploaded successfully!")
    if st.button("Process and Generate Podcast"):
        with st.spinner("Extracting text from PDF..."):
            with pdfplumber.open(tmp_pdf_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    text = page.extract_text(x_tolerance=2)
                    if text:
                        all_text += text + "\n"
        st.success("Text extracted!")
        st.write("Generating podcast conversation with Gemini...")
        conversation = convert_to_conversation(all_text)
        st.success("Conversation generated!")
        st.text_area("Podcast Conversation", conversation, height=300)
        st.write("Synthesizing audio with Edge TTS...")
        audio_bytes = asyncio.run(convert_to_audio(conversation))
        if audio_bytes:
            # st.audio(audio_bytes, format='audio/mp3')
            st.success("Podcast audio ready! Download below.")
            st.download_button("Download Podcast Audio", audio_bytes, file_name="podcast_audio.mp3")
        else:
            st.error("Audio synthesis failed. Please try a different PDF or check your configuration.") 