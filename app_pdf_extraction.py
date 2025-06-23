from langchain_community.document_loaders import PyPDFLoader
import fitz  # PyMuPDF
from PIL import Image
import io
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyA8HQwl-M53R9uxcCF8SYUN9nuxtzReuTc"
genai.configure(api_key=GEMINI_API_KEY)

def analyze_image_with_gemini(image: Image.Image, prompt="Describe this image in detail."):
    model = genai.GenerativeModel("gemini-1.5-flash-vision")
    with io.BytesIO() as output:
        image.save(output, format="PNG")
        image_bytes = output.getvalue()
    gemini_image = {"mime_type": "image/png", "data": image_bytes}
    response = model.generate_content([prompt, gemini_image])
    return response.text

# Path to the PDF file to extract text from
pdf_path = "PDF/Attention_is_all_you_need.PDF"

# Use LangChain's PyPDFLoader to extract text
loader = PyPDFLoader(pdf_path)
documents = loader.load()

# Open the PDF with PyMuPDF for image extraction
pdf_doc = fitz.open(pdf_path)

all_text = ""
for i, doc in enumerate(documents):
    page_text = doc.page_content
    # Extract images from the same page
    page = pdf_doc[i]
    images = page.get_images(full=True)
    vision_texts = []
    for img_index, img in enumerate(images):
        xref = img[0]
        base_image = pdf_doc.extract_image(xref)
        image_bytes = base_image["image"]
        image = Image.open(io.BytesIO(image_bytes))
        # Use Gemini Vision to analyze the image
        vision_desc = analyze_image_with_gemini(image)
        if vision_desc.strip():
            vision_texts.append(f"[Image {img_index+1} Gemini Vision]:\n{vision_desc.strip()}")
    # Combine text and Vision results
    if vision_texts:
        page_text += "\n" + "\n".join(vision_texts)
    all_text += f"\n--- Page {i+1} ---\n" + page_text

print(all_text)

# Save the combined output to a file
output_file = "Text_extracted_pdf_with_gemini_vision.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(all_text)

print(f"Extracted text (with Gemini Vision) saved to {output_file}")
