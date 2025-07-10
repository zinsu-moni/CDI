"""
FastAPI Crop Disease Identification API
---------------------------------------
A REST API for crop disease identification using KindWise API
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import base64
import requests
import json
from PIL import Image
import io
import tempfile
from typing import Optional
import shutil
import subprocess
import sys

app = FastAPI(title="Crop Disease Identification API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Configuration
API_URL = "https://crop.kindwise.com/api/v1/identification"
API_KEY = "u12lFbhGXOPacNJgi4pqK2scNsm34OryIiw99IIPJLKzjgntD5"

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_upload_form():
    """Serve a simple HTML form for testing the API"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crop Disease Identification</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
            .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
            .button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .button:hover { background: #45a049; }
            .results { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .loading { display: none; color: #666; }
            #imagePreview { max-width: 300px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌱 Crop Disease Identification</h1>
            <p>Upload an image of your crop to identify the plant species and detect any diseases.</p>
            
            <div class="upload-area">
                <input type="file" id="imageInput" accept="image/*" style="display: none;">
                <button class="button" onclick="document.getElementById('imageInput').click()">Choose Image</button>
                <p>or drag and drop an image here</p>
                <img id="imagePreview" style="display: none;">
            </div>
            
            <button class="button" id="analyzeBtn" onclick="analyzeImage()" disabled>Analyze Crop</button>
            <button class="button" id="chatbotBtn" onclick="sendToChatbot()" disabled style="background: #2196F3;">Send to ChatBot</button>
            
            <div class="loading" id="loading">🔍 Analyzing your crop image...</div>
            
            <div class="results" id="results" style="display: none;">
                <h3>Analysis Results:</h3>
                <div id="resultsContent"></div>
            </div>
        </div>

        <script>
            let analysisResults = null;
            let uploadedFile = null;

            document.getElementById('imageInput').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    uploadedFile = file;
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.getElementById('imagePreview');
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                        document.getElementById('analyzeBtn').disabled = false;
                    };
                    reader.readAsDataURL(file);
                }
            });

            async function analyzeImage() {
                if (!uploadedFile) return;

                const formData = new FormData();
                formData.append('file', uploadedFile);

                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';

                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    
                    if (result.success) {
                        analysisResults = result;
                        displayResults(result);
                        document.getElementById('chatbotBtn').disabled = false;
                    } else {
                        alert('Analysis failed: ' + result.error);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            }

            function displayResults(result) {
                let html = '<h4>🌾 Identified Crops:</h4>';
                
                if (result.crops && result.crops.length > 0) {
                    result.crops.forEach((crop, index) => {
                        html += `<div style="margin: 10px 0; padding: 10px; background: #e8f5e8; border-radius: 5px;">
                            <strong>Crop ${index + 1}:</strong> ${crop.name} (${crop.scientific_name})<br>
                            <strong>Confidence:</strong> ${crop.confidence}%
                        </div>`;
                    });
                } else {
                    html += '<p>No crops identified.</p>';
                }

                if (result.diseases && result.diseases.length > 0) {
                    html += '<h4>🏥 Plant Health Conditions:</h4>';
                    result.diseases.forEach((disease, index) => {
                        html += `<div style="margin: 10px 0; padding: 10px; background: #ffe8e8; border-radius: 5px;">
                            <strong>Condition ${index + 1}:</strong> ${disease.name}<br>
                            <strong>Confidence:</strong> ${disease.confidence}%
                        </div>`;
                    });
                } else {
                    html += '<h4>✅ Plant Health:</h4><p>No diseases detected. The plant appears healthy!</p>';
                }

                document.getElementById('resultsContent').innerHTML = html;
                document.getElementById('results').style.display = 'block';
            }

            async function sendToChatbot() {
                if (!analysisResults) {
                    alert('No analysis results to send to chatbot.');
                    return;
                }

                try {
                    const response = await fetch('/send-to-chatbot', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(analysisResults)
                    });

                    const result = await response.json();
                    
                    if (result.success) {
                        alert('ChatBot launched successfully! Check for a new window or tab.');
                    } else {
                        alert('Failed to launch ChatBot: ' + result.error);
                    }
                } catch (error) {
                    alert('Error launching ChatBot: ' + error.message);
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/analyze")
async def analyze_crop_image(file: UploadFile = File(...)):
    """Analyze uploaded crop image using KindWise API"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process image
        image_bytes = await file.read()
        
        # Validate image can be opened
        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Resize if too large
            max_size = 1024
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.LANCZOS)
            
            # Convert to RGB and save as JPEG
            image = image.convert('RGB')
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=95)
            image_bytes = output_buffer.getvalue()
            
        except Exception as img_err:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(img_err)}")
        
        # Encode image for API
        encoded_string = base64.b64encode(image_bytes).decode('utf-8')
        
        # Prepare API request
        headers = {
            'Content-Type': 'application/json',
            'Api-Key': API_KEY
        }
        
        payload = {
            'images': [encoded_string],
            'similar_images': True
        }
        
        # Call KindWise API
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Parse results
            crops = []
            diseases = []
            
            if 'result' in data and data['result']:
                result_data = data['result']
                
                # Extract crop information
                if 'crop' in result_data and 'suggestions' in result_data['crop']:
                    for crop in result_data['crop']['suggestions']:
                        crops.append({
                            'name': crop.get('name', 'Unknown'),
                            'scientific_name': crop.get('scientific_name', ''),
                            'confidence': round(crop.get('probability', 0) * 100, 2)
                        })
                
                # Extract disease information
                if 'disease' in result_data and 'suggestions' in result_data['disease']:
                    for disease in result_data['disease']['suggestions']:
                        diseases.append({
                            'name': disease.get('name', 'Unknown'),
                            'confidence': round(disease.get('probability', 0) * 100, 2)
                        })
            
            # Save results for chatbot integration
            result_summary = {
                'success': True,
                'crops': crops,
                'diseases': diseases,
                'raw_data': data,
                'image_filename': file.filename
            }
            
            # Save to temporary files for chatbot integration
            crop_data_file = os.path.join(UPLOAD_DIR, "latest_analysis.json")
            with open(crop_data_file, "w") as f:
                json.dump(result_summary, f)
            
            # Save the analyzed image
            image_file_path = os.path.join(UPLOAD_DIR, "latest_image.jpg")
            with open(image_file_path, "wb") as f:
                f.write(image_bytes)
            
            return result_summary
            
        else:
            error_detail = f"API returned status code {response.status_code}"
            try:
                error_detail = response.json()
            except:
                try:
                    error_detail = response.text
                except:
                    pass
            
            raise HTTPException(status_code=500, detail=f"API Error: {error_detail}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-to-chatbot")
async def send_to_chatbot(analysis_data: dict):
    """Launch chatbot with analysis results"""
    try:
        # Create formatted summary
        crop_summary = "Crop Analysis Results:\n\n"
        
        if analysis_data.get('crops'):
            crop_summary += "Identified Crops:\n"
            for crop in analysis_data['crops']:
                crop_summary += f"- {crop['name']} ({crop['scientific_name']}): {crop['confidence']}% confidence\n"
        
        if analysis_data.get('diseases'):
            crop_summary += "\nPlant Health Conditions:\n"
            for disease in analysis_data['diseases']:
                crop_summary += f"- {disease['name']}: {disease['confidence']}% confidence\n"
        elif analysis_data.get('crops'):
            crop_summary += "\nNo diseases detected. The plant appears healthy.\n"
        
        # Save data for chatbot
        chatbot_data = {
            "crop_summary": crop_summary,
            "raw_data": analysis_data.get('raw_data', {})
        }
        
        crop_data_file = os.path.join(UPLOAD_DIR, "crop_analysis_data.json")
        with open(crop_data_file, "w") as f:
            json.dump(chatbot_data, f)
        
        # Get paths
        image_file_path = os.path.join(UPLOAD_DIR, "latest_image.jpg")
        launcher_path = os.path.join("..", "chat_bot", "launch_chatbot.py")
        
        # Launch chatbot
        try:
            subprocess.Popen([
                sys.executable, launcher_path,
                "--analysis-data", os.path.abspath(crop_data_file),
                "--image-path", os.path.abspath(image_file_path)
            ])
            
            return {"success": True, "message": "ChatBot launched successfully"}
            
        except Exception as launch_error:
            return {"success": False, "error": f"Failed to launch ChatBot: {str(launch_error)}"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Crop Disease Identification API"}

@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "Crop Disease Identification API",
        "version": "1.0.0",
        "description": "REST API for crop disease identification using KindWise API",
        "endpoints": {
            "/": "Upload form (HTML interface)",
            "/analyze": "POST - Analyze crop image",
            "/send-to-chatbot": "POST - Launch chatbot with results",
            "/health": "GET - Health check",
            "/api/info": "GET - API information"
        }
    }

if __name__ == "__main__":
    print("🌱 Starting Crop Disease Identification API...")
    print("📖 Documentation: http://localhost:8000/docs")
    print("🌐 Web Interface: http://localhost:8000")
    
    uvicorn.run(
        "main_fastapi:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
