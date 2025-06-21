import pdfplumber  # Library for extracting text from PDF files
import google.generativeai as genai  # Google's Generative AI library for Gemini
import os  # For environment variables
import asyncio  # For async operations
import edge_tts  # Microsoft Edge Text-to-Speech
import re  # For text parsing

# Path to the PDF file to extract text from
pdf_path = "PDF/Attention_is_all_you_need.PDF"
# Output file where the extracted text will be saved
output_file = "Text_extracted_pdf.md"
# Output file for the conversation format
conversation_output = "conversation_format.md"
# Output audio file
audio_output = "podcast_audio.mp3"

GOOGLE_API_KEY = 'AIzaSyA8HQwl-M53R9uxcCF8SYUN9nuxtzReuTc'

# Configure Google Generative AI with your API key
# Pass the actual API key string, not an environment variable lookup
genai.configure(api_key=GOOGLE_API_KEY)

# Open the PDF file using pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    all_text = ""  # Initialize a string to hold all extracted text
    # Iterate through each page in the PDF
    for page in pdf.pages:
        # Extract text from the page with a specified x_tolerance to improve space handling
        text = page.extract_text(x_tolerance=2)
        if text:
            all_text += text + "\n"  # Add the extracted text and a newline

# Write the extracted text to the output file in UTF-8 encoding
with open(output_file, "w", encoding="utf-8") as f:
    f.write(all_text)

print(f"Extracted text saved to {output_file}")

# Function to convert text to conversation format using Gemini
def convert_to_conversation(text_content):
    """Convert research paper text to podcast-style conversation using Gemini Flash 1.5"""
    
    # Create the prompt for conversation conversion
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
    
    try:
        # Use Gemini Flash 1.5 model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generate the conversation
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        return f"Error generating conversation: {str(e)}"

# Function to parse conversation and extract speaker segments
def parse_conversation(conversation_text):
    """Parse conversation text and extract speaker segments for TTS"""
    segments = []
    # Regex to match 'Alex:' or 'Samantha:' at the start of a line, case-insensitive, with optional spaces after colon
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
            # Save previous segment if exists
            if current_speaker and current_text:
                segments.append((current_speaker, current_text.strip()))
            current_speaker = match.group(1).capitalize()  # 'Alex' or 'Samantha'
            current_text = match.group(2).strip()
        else:
            # Continue current speaker's text
            if current_speaker:
                current_text += " " + line
    # Add the last segment
    if current_speaker and current_text:
        segments.append((current_speaker, current_text.strip()))
    return segments

def remove_timestamps(text):
    """Remove [hh:mm:ss] or [mm:ss] timestamps from text."""
    return re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', '', text)

# Function to convert conversation to audio using Edge TTS
async def convert_to_audio(conversation_text):
    """Convert conversation text to audio using Microsoft Edge TTS"""
    
    # Remove timestamps from the conversation text
    conversation_text = remove_timestamps(conversation_text)
    
    # Parse conversation into speaker segments
    segments = parse_conversation(conversation_text)
    
    # Define voices and rates for each speaker
    voices = {
        'Alex': ('en-US-ChristopherNeural', '+30%'),      # Faster male voice
        'Samantha': ('en-US-JennyNeural', '+0%')           # Normal female voice
    }
    
    print(f"Converting {len(segments)} conversation segments to audio...")
    
    # Generate audio for each segment
    audio_segments = []
    for i, (speaker, text) in enumerate(segments):
        if not text.strip():
            continue
            
        print(f"Processing segment {i+1}/{len(segments)}: {speaker}")
        
        try:
            # Set voice and rate for current speaker
            voice, rate = voices[speaker]
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            
            # Generate audio using stream method
            audio_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            audio_segments.append(audio_data)
            
        except Exception as e:
            print(f"Error processing segment {i+1}: {e}")
            continue
    
    # Combine all audio segments
    if audio_segments:
        combined_audio = b''.join(audio_segments)
        
        # Save to file
        with open(audio_output, 'wb') as f:
            f.write(combined_audio)
        
        print(f"Audio saved to {audio_output}")
        return True
    else:
        print("No audio segments were generated successfully")
        return False

# Convert the extracted text to conversation format
print("Converting to conversation format using Gemini Flash 1.5...")
conversation = convert_to_conversation(all_text)

# Save the conversation to a file
with open(conversation_output, "w", encoding="utf-8") as f:
    f.write(conversation)

print(f"Conversation format saved to {conversation_output}")

# Convert conversation to audio
print("Converting conversation to audio using Microsoft Edge TTS...")
asyncio.run(convert_to_audio(conversation))

print("Process completed!")
