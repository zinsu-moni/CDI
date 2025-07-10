"""
FastAPI server for Crop Disease Identification Chatbot

This server replaces the Streamlit UI with a FastAPI backend that serves
the static HTML/JS frontend and provides API endpoints for chat and image analysis.
"""

import os
import base64
import json
import io
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
from openai import OpenAI
from PIL import Image
import numpy as np
import uuid

# Import the crop analyzer module
from crop_analyzer import CropAnalyzer

# Create FastAPI app
app = FastAPI(title="Crop Disease Identifier API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=current_dir), name="static")

# Create a place to store chat histories by session
chat_histories = {}

# Models
class ChatRequest(BaseModel):
    content: Optional[str] = None
    image_base64: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# OpenAI client configuration
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# Function to process chat with DeepSeek API
def process_with_deepseek(messages, crop_analysis=None):
    try:
        # Prepare messages for the API (remove image_base64, only send text)
        api_messages = [
            {k: v for k, v in m.items() if k != "image_base64"} for m in messages[-10:]
        ]
        
        # Add crop analysis context if available
        if crop_analysis:
            context = "You are a crop disease identification expert. The user has uploaded an image that has been analyzed. "
            
            # Handle different response formats
            
            # Format 1: Standard 'analysis' structure
            if "analysis" in crop_analysis:
                analysis = crop_analysis["analysis"]
                
                # Add crop information
                if "plant_species" in analysis and analysis["plant_species"]:
                    crops = analysis["plant_species"]
                    crop_names = [f"{c['common_name']} ({c['scientific_name']})" for c in crops if "common_name" in c and "scientific_name" in c]
                    context += f"The image shows {', '.join(crop_names)}. "
                
                # Add disease information
                if "diseases" in analysis and analysis["diseases"]:
                    diseases = analysis["diseases"]
                    disease_names = [d["name"] for d in diseases if "name" in d]
                    context += f"The plant shows signs of {', '.join(disease_names)}. "
                    
                    # Add treatment information
                    for disease in diseases:
                        if 'treatments' in disease and disease['treatments']:
                            context += f"For {disease.get('name', 'this condition')}, recommended treatments include: {', '.join(disease['treatments'])}. "
                else:
                    # If no disease was detected, request symptoms
                    context += "No specific disease was detected with high confidence. Please ask the user about symptoms they observe. "
                    
                # Add health assessment if available
                if "health_assessment" in analysis:
                    health = analysis["health_assessment"]
                    context += f"Overall plant health assessment: {health.get('status', 'Unknown')}. "
                    
                    if 'recommendations' in health and health['recommendations']:
                        context += f"General recommendations include: {', '.join(health['recommendations'])}. "
            
            # Format 2: 'results' structure
            elif "results" in crop_analysis:
                results = crop_analysis["results"]
                
                # Handle results as list
                if isinstance(results, list) and results:
                    result = results[0]  # Take the first result
                    
                    # Add crop information
                    if "species" in result:
                        species = result["species"]
                        crop_name = species.get("common_name", "Unknown")
                        scientific_name = species.get("scientific_name", "")
                        context += f"The image shows {crop_name} ({scientific_name}). "
                    
                    # Add disease information
                    if "diseases" in result and result["diseases"]:
                        diseases = result["diseases"]
                        disease_names = [d["name"] for d in diseases if "name" in d]
                        context += f"The plant shows signs of {', '.join(disease_names)}. "
                        
                        # Add treatment information if available
                        for disease in diseases:
                            if "treatment" in disease:
                                context += f"For {disease.get('name', 'this condition')}, recommended treatment: {disease['treatment']}. "
                    else:
                        context += "No specific disease was detected with high confidence. Please ask the user about symptoms they observe. "
                
                # Handle results as direct object
                elif isinstance(results, dict):
                    # Add crop information
                    if "species" in results:
                        species = results["species"]
                        crop_name = species.get("common_name", "Unknown")
                        scientific_name = species.get("scientific_name", "")
                        context += f"The image shows {crop_name} ({scientific_name}). "
                    
                    # Add disease information
                    if "diseases" in results and results["diseases"]:
                        diseases = results["diseases"]
                        disease_names = [d["name"] for d in diseases if "name" in d]
                        context += f"The plant shows signs of {', '.join(disease_names)}. "
                    else:
                        context += "No specific disease was detected with high confidence. Please ask the user about symptoms they observe. "
            
            # Add this context to the messages
            api_messages.insert(0, {
                "role": "system",
                "content": context
            })
                
                context += "Provide detailed advice on cultivation, disease management, and best practices for this crop."
                

        
        # Send to DeepSeek API
        completion = openai_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Crop Disease ChatBot",
            },
            extra_body={},
            model="deepseek/deepseek-chat:free",
            messages=api_messages,
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error in DeepSeek API: {str(e)}")
        return f"I encountered an error while processing your request: {str(e)}"

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open(os.path.join(current_dir, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/script.js")
async def get_script():
    """Serve the JavaScript file"""
    return FileResponse(os.path.join(current_dir, "script.js"))

@app.get("/style.css")
async def get_style():
    """Serve the CSS file"""
    return FileResponse(os.path.join(current_dir, "style.css"))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages and image analysis"""
    # Get or create session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Initialize chat history for this session if needed
    if session_id not in chat_histories:
        chat_histories[session_id] = [
            {"role": "system", "content": "You are a helpful assistant for crop disease identification and advice."}
        ]
    
    # Get message content
    user_content = request.content or ""
    
    # Add user message to history (if not empty)
    if user_content:
        chat_histories[session_id].append({"role": "user", "content": user_content})
    
    # Process image if provided
    crop_analysis_result = None
    if request.image_base64:
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(request.image_base64)
            
            # Use the CropAnalyzer to analyze the image
            analyzer = CropAnalyzer()
            analysis_results = analyzer.analyze_image_bytes(image_bytes)
            
            if analysis_results["success"]:
                # Get the formatted summary
                crop_summary = analysis_results["summary"]
                
                # Store the analysis result for DeepSeek context
                crop_analysis_result = analysis_results["api_response"]
                
                # Add user message with image indicator
                if not user_content:  # Only add this if no text was provided
                    chat_histories[session_id].append({
                        "role": "user", 
                        "content": "[Image uploaded for crop analysis]"
                    })
                
                # Add analysis results as an assistant message
                chat_histories[session_id].append({
                    "role": "assistant",
                    "content": f"I've analyzed your crop image and here are the results:\n\n{crop_summary}\n\nWould you like more specific information about these crops or advice on cultivation and disease management?"
                })
                
                # Process with DeepSeek directly and return
                return ChatResponse(
                    response=chat_histories[session_id][-1]["content"],
                    session_id=session_id
                )
            else:
                # If analysis failed, add error message
                error_msg = analysis_results.get("error", "Unknown error occurred during analysis")
                chat_histories[session_id].append({
                    "role": "assistant",
                    "content": f"I encountered an issue while analyzing your image: {error_msg}\n\nPlease try again with a clearer image or check your internet connection."
                })
                
                return ChatResponse(
                    response=chat_histories[session_id][-1]["content"],
                    session_id=session_id
                )
        except Exception as e:
            error_message = f"Error processing image: {str(e)}"
            chat_histories[session_id].append({
                "role": "assistant",
                "content": error_message
            })
            return ChatResponse(response=error_message, session_id=session_id)
    
    # Process with DeepSeek if we have text input
    if user_content or not request.image_base64:
        bot_reply = process_with_deepseek(chat_histories[session_id], crop_analysis_result)
        chat_histories[session_id].append({"role": "assistant", "content": bot_reply})
    
    # Return the latest response
    return ChatResponse(
        response=chat_histories[session_id][-1]["content"],
        session_id=session_id
    )

# Run this with: uvicorn fast_api:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fast_api:app", host="0.0.0.0", port=8000, reload=True)
