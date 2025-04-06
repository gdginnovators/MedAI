from flask import Flask, render_template, request, flash
import google.generativeai as genai
from PIL import Image
import io
import textwrap
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for flash messages

# ===== Configuration =====
API_KEY = "AIzaSyDPmukhY7Ejs9TEwaRyxtCMiTZVAsJC2dk"  # Replace with your actual key
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Gemini
genai.configure(api_key=API_KEY)
vision_model = genai.GenerativeModel('gemini-1.5-pro')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get form data
            patient_info = request.form.get('patient_info', '').strip()
            analysis_date = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            # Process reports
            past_data, is_past_image = process_uploaded_file('past_report')
            present_data, is_present_image = process_uploaded_file('present_report')
            
            # Analyze reports
            analysis = analyze_reports(
                vision_model,
                past_data,
                present_data,
                is_past_image,
                is_present_image
            )
            
            return render_template('result.html',
                                patient_info=patient_info,
                                analysis_date=analysis_date,
                                analysis=analysis)
            
        except Exception as e:
            flash(f"Error: {str(e)}", 'error')
            return render_template('result.html')
    
    return render_template('report.html')

def process_uploaded_file(field_name):
    if field_name not in request.files:
        raise ValueError(f"No {field_name} file uploaded")
    
    file = request.files[field_name]
    if file.filename == '':
        raise ValueError(f"No file selected for {field_name}")
    
    # Check if file is an image
    is_image = file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))
    
    if is_image:
        # Process image
        image_bytes = file.read()
        return image_bytes, True
    else:
        # Process text file
        text_content = file.read().decode('utf-8')
        return text_content, False

def analyze_reports(vision_model, past_data, present_data, is_past_image, is_present_image):
    prompt = """
    🏥 **Medical Report Analysis** 🏥

    **Instructions:** 
    1. Compare the past and present medical reports.
    2. Identify significant differences in:
       - **Vital signs (BP, glucose, cholesterol, etc.)**
       - **Imaging results (X-ray, MRI, CT scan, ultrasound)**
       - **Doctor's Notes & Prescriptions**
    3. Highlight **critical warnings** if detected.
    4. Suggest **next steps** for doctors.

    **Output Format:**
    - 🔍 **Key Differences**
    - ⚠️ **Risk Factors**
    - ✅ **Recommended Actions**
    """

    contents = []

    # Add past data
    if is_past_image:
        contents.append({"mime_type": "image/jpeg", "data": past_data})
    else:
        contents.append(f"📜 **Past Report:**\n{past_data}")

    # Add present data
    if is_present_image:
        contents.append({"mime_type": "image/jpeg", "data": present_data})
    else:
        contents.append(f"📜 **Present Report:**\n{present_data}")

    contents.append(prompt)

    response = vision_model.generate_content(contents)
    return response.text

if __name__ == '__main__':
    app.run(debug=True)