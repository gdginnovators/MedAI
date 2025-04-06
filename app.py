from flask import Flask, render_template, request, flash, redirect, url_for
import google.generativeai as genai
from PIL import Image
import io
import os
import pytesseract
import markdown
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ===== Configuration =====
API_KEY = "AIzaSyDPmukhY7Ejs9TEwaRyxtCMiTZVAsJC2dk"  # Replace with your actual key
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Gemini
genai.configure(api_key=API_KEY)

# ===== Routes for All Features =====

@app.route('/')
def home():
    """Home page with all feature options"""
    return render_template('index.html')

@app.route('/ecg-analysis')
def ecg_analysis():
    """ECG analysis feature"""
    return render_template('ecg.html')

@app.route('/medical-chatbot')
def medical_chatbot():
    """Medical chatbot feature"""
    return render_template('chatbot.html')

@app.route('/report-comparison')
def report_comparison():
    """Report comparison feature"""
    return render_template('report.html')

@app.route('/analyze-ecg', methods=['POST'])
def analyze_ecg():
    """Process ECG analysis"""
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('ecg_analysis'))
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('ecg_analysis'))
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Process file and generate analysis (your existing ECG analysis code)
            # ...
            
            return render_template('ecg_result.html', result=result)
            
    except Exception as e:
        flash(f'Error processing ECG: {str(e)}', 'error')
        return redirect(url_for('ecg_analysis'))

@app.route('/chat', methods=['POST'])
def chat_handler():
    """Handle medical chatbot requests"""
    try:
        user_message = request.json['message']
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(user_message)
        return jsonify({'status': 'success', 'response': response.text})
    except Exception as e:
        return jsonify({'status': 'error', 'response': str(e)})

@app.route('/compare-reports', methods=['POST'])
def compare_reports():
    """Process report comparison"""
    try:
        patient_info = request.form.get('patient_info', '').strip()
        analysis_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        past_data, is_past_image = process_uploaded_file('past_report')
        present_data, is_present_image = process_uploaded_file('present_report')
        
        analysis = analyze_reports(past_data, present_data, is_past_image, is_present_image)
        
        return render_template('report_result.html',
                            patient_info=patient_info,
                            analysis_date=analysis_date,
                            analysis=analysis)
        
    except Exception as e:
        flash(f'Error comparing reports: {str(e)}', 'error')
        return redirect(url_for('report_comparison'))

# ===== Helper Functions =====

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'jpg', 'jpeg', 'png'}

def process_uploaded_file(field_name):
    if field_name not in request.files:
        raise ValueError(f"No {field_name} file uploaded")
    
    file = request.files[field_name]
    if file.filename == '':
        raise ValueError(f"No file selected for {field_name}")
    
    is_image = file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))
    
    if is_image:
        return file.read(), True
    else:
        return file.read().decode('utf-8'), False

def analyze_reports(past_data, present_data, is_past_image, is_present_image):
    vision_model = genai.GenerativeModel('gemini-pro-vision')
    
    prompt = """Compare these medical reports and provide:
    1. Key differences in findings
    2. Changes in medication/treatment
    3. Potential health trends
    4. Recommended next steps"""
    
    contents = []
    
    if is_past_image:
        contents.append({"mime_type": "image/jpeg", "data": past_data})
    else:
        contents.append(f"Past Report:\n{past_data}")
    
    if is_present_image:
        contents.append({"mime_type": "image/jpeg", "data": present_data})
    else:
        contents.append(f"Present Report:\n{present_data}")
    
    contents.append(prompt)
    
    response = vision_model.generate_content(contents)
    return response.text

if __name__ == '__main__':
    app.run(debug=True)