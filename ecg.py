import os
import logging
from flask import Flask, request, render_template, redirect, flash, url_for
from werkzeug.utils import secure_filename
import PyPDF2
from PIL import Image
import io
import base64
import google.generativeai as genai
import pytesseract
import markdown

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
logging.basicConfig(level=logging.DEBUG)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB max file size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Configure Gemini API
GEMINI_MODEL = "gemini-1.5-pro"  # Updated to use the latest model
genai.configure(api_key="AIzaSyArihOGcyK5KcQR4ntIqNga6bSoq7kM7Yo")

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def setup_gemini():
    """Initialize Gemini API with error handling"""
    try:
        genai.configure(api_key="AIzaSyArihOGcyK5KcQR4ntIqNga6bSoq7kM7Yo")
        return True
    except Exception as e:
        logging.error(f"Failed to configure Gemini API: {str(e)}")
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_images_from_pdf(pdf_path):
    """Extract images from PDF file and convert to base64"""
    images_data = []
    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                if hasattr(page, 'images'):
                    for image_file_object in page.images:
                        try:
                            image = Image.open(io.BytesIO(image_file_object.data))
                            buffered = io.BytesIO()
                            image.save(buffered, format="PNG")
                            img_str = base64.b64encode(buffered.getvalue()).decode()
                            images_data.append(img_str)
                        except Exception as e:
                            logging.warning(f"Failed to process image: {str(e)}")
    except Exception as e:
        logging.error(f"Error extracting images: {str(e)}")
    return images_data

def extract_text_from_image(image_path):
    """Extract text from image using OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image: {str(e)}")
        return ""

def get_scan_type(text):
    """Determine the type of scan from the text content"""
    text_lower = text.lower()
    scan_types = {
        'electrocardiogram': 'ECG',
        'ecg': 'ECG',
        'ekg': 'ECG',
        'electrocardiography': 'ECG'
    }
    
    for key, value in scan_types.items():
        if key in text_lower:
            return value
    return 'ECG'  # Default to ECG if no specific type found

def analyze_medical_scan(scan_type, combined_text, image_count):
    """Generate analysis using Gemini API"""
    try:
        logging.debug(f"Initializing Gemini model with type: {GEMINI_MODEL}")
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        prompt = f"""
        As a professional cardiologist, analyze this {scan_type} report in detail.
        Provide a comprehensive analysis including:

        1. Clinical Findings:
        - Rhythm analysis
        - Rate calculation
        - Axis determination
        - Intervals (PR, QRS, QT)
        - Waveform abnormalities

        2. Interpretation:
        - Normal vs abnormal findings
        - Potential cardiac conditions suggested
        - Any acute findings requiring immediate attention

        3. Technical Quality:
        - Assessment of recording quality
        - Artifacts or limitations noted

        4. Recommendations:
        - Suggested follow-up tests if needed
        - When to consult a cardiologist
        - Any urgent actions required

        Report details:
        - Number of images/tracings: {image_count}
        - Extracted text content: {combined_text}

        Provide your analysis in clear, professional medical terminology 
        but also include patient-friendly explanations where appropriate.
        Format your response with proper headings and bullet points for clarity.
        """
        
        logging.debug("Sending request to Gemini API")
        response = model.generate_content(prompt)
        logging.debug("Received response from Gemini API")
        
        if not response or not hasattr(response, 'text'):
            raise ValueError("Invalid response from Gemini API")
            
        return response.text
    except Exception as e:
        logging.error(f"Error generating analysis: {str(e)}")
        raise

@app.route('/', methods=['GET', 'POST'])
def index():
    if not setup_gemini():
        flash('Failed to initialize AI service. Please try again later.', 'error')
        return render_template("ecg.html", result=None)

    result = None
    if request.method == 'POST':
        logging.debug("Received a POST request.")
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            logging.debug("No file part in request")
            flash('No file selected', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            logging.debug("No selected file")
            flash('No file selected', 'error')
            return redirect(request.url)
            
        # Check file size
        if request.content_length > MAX_FILE_SIZE:
            logging.debug("File too large")
            flash(f'File size exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB limit', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            file_path = None
            try:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logging.debug(f"Saving file to: {file_path}")
                file.save(file_path)
                
                # Process text and images
                combined_text = ""
                if filename.lower().endswith('.pdf'):
                    logging.debug("Processing PDF file")
                    with open(file_path, "rb") as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        for page_num, page in enumerate(pdf_reader.pages):
                            page_text = page.extract_text()
                            if page_text:
                                combined_text += page_text
                            logging.debug(f"Extracted text from page {page_num}")
                    images_data = extract_images_from_pdf(file_path)
                else:  # Image file
                    logging.debug("Processing image file")
                    combined_text = extract_text_from_image(file_path)
                    with open(file_path, "rb") as img_file:
                        img_data = base64.b64encode(img_file.read()).decode()
                        images_data = [img_data]
                
                logging.debug(f"Extracted text length: {len(combined_text)}")
                scan_type = get_scan_type(combined_text)
                image_count = len(images_data)
                logging.debug(f"Detected scan type: {scan_type}, Image count: {image_count}")
                
                # Generate analysis
                logging.debug("Generating analysis")
                analysis_text = analyze_medical_scan(scan_type, combined_text, image_count)
                analysis_html = markdown.markdown(analysis_text)
                
                result = {
                    'analysis': analysis_text,
                    'analysis_html': analysis_html,
                    'scan_type': scan_type,
                    'image_count': image_count,
                    'images': images_data
                }
                logging.debug("Analysis complete")
                
            except Exception as e:
                logging.exception("Error processing file:")
                flash(f"Error processing file: {str(e)}", 'error')
                return redirect(request.url)
            finally:
                # Clean up uploaded file
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logging.debug("Temporary file removed after processing.")
        else:
            logging.debug("Invalid file type")
            flash('Only PDF and image files are allowed', 'error')
            return redirect(request.url)
            
    return render_template("ecg.html", result=result)

if __name__ == '__main__':
    app.run(debug=True)