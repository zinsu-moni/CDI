"""
Enhanced Crop Disease Chatbot with DeepSeek AI

This version has improved handling of the text input clearing
and overall better state management.
"""

import streamlit as st
from openai import OpenAI
import base64
from PIL import Image
import numpy as np
import io
import argparse
import os
import json
import sys
import tempfile
import time
from crop_analyzer import CropAnalyzer

# Set page configuration
st.set_page_config(page_title="Crop Disease ChatBot", layout="centered")
st.title("Crop Disease ChatBot")

# Parse command-line arguments if provided
analysis_data_path = None
image_path = None

# Only parse arguments if running via streamlit
if "streamlit" in sys.modules:
    try:
        parser = argparse.ArgumentParser(description='Crop Disease Chatbot with Analysis Data')
        parser.add_argument('--analysis-data', type=str, help='Path to the crop analysis data JSON file')
        parser.add_argument('--image-path', type=str, help='Path to the analyzed crop image')
        
        # Get arguments while ignoring Streamlit's own arguments
        args, unknown = parser.parse_known_args()
        analysis_data_path = args.analysis_data
        image_path = args.image_path
    except:
        # If argument parsing fails, continue without arguments
        pass

# Load crop analysis data if provided
crop_analysis = None
if analysis_data_path and os.path.exists(analysis_data_path):
    try:
        with open(analysis_data_path, 'r') as f:
            crop_analysis = json.load(f)
        st.sidebar.success("Crop analysis data loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error loading crop analysis data: {str(e)}")

# Load analyzed image if provided
analyzed_image = None
if image_path and os.path.exists(image_path):
    try:
        analyzed_image = Image.open(image_path)
        st.sidebar.image(analyzed_image, caption="Analyzed Crop Image", use_column_width=True)
    except Exception as e:
        st.sidebar.error(f"Error loading image: {str(e)}")

# Initialize session state for messages if not already present
if "messages" not in st.session_state:
    initial_system_message = {
        "role": "system", 
        "content": "You are a helpful assistant for crop disease identification and advice. "
    }
    
    if crop_analysis:
        # Add the crop analysis data to the initial system prompt
        initial_system_message["content"] += (
            f"The user has already analyzed a crop image with the following results: "
            f"{crop_analysis.get('crop_summary', 'No summary available')}. "
            f"Use this information to provide detailed advice about growing conditions, "
            f"disease treatment, and best practices for the identified crop."
        )
        
        # Add analysis data as the first assistant message
        st.session_state["messages"] = [
            initial_system_message,
            {
                "role": "assistant",
                "content": (
                    f"I've analyzed your crop image and here are the results:\n\n"
                    f"{crop_analysis.get('crop_summary', 'No analysis results available.')}\n\n"
                    f"How can I help you with more information about this crop or any advice on cultivation or treatment?"
                )
            }
        ]
    else:
        st.session_state["messages"] = [initial_system_message]

# Flag for detecting if message was just sent
if "message_sent" not in st.session_state:
    st.session_state["message_sent"] = False

# Display chat messages
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
        if msg.get("image_base64"):
            st.image(base64.b64decode(msg["image_base64"]), caption="Uploaded Image", use_container_width=True)
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])
    # System messages are not displayed

# If analyzed image is already loaded, display it
if analyzed_image and 'displayed_analysis_image' not in st.session_state:
    st.image(analyzed_image, caption="Analyzed Crop Image", use_container_width=True)
    st.session_state['displayed_analysis_image'] = True

# Function to process messages with DeepSeek API
def process_with_api():
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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",
        )
        
        # Prepare messages for the API (remove image_base64, only send text)
        api_messages = [
            {k: v for k, v in m.items() if k != "image_base64"} for m in st.session_state["messages"][-10:]
        ]
        
        # Add crop analysis context to the prompt if available
        # First check if we have analysis data from the file
        if crop_analysis and not any("crop_summary" in str(m.get("content", "")) for m in api_messages[:3]):
            api_messages.insert(1, {
                "role": "system",
                "content": f"The user has analyzed a crop image with the following results: {crop_analysis.get('crop_summary', 'No summary available')}. Use this information in your responses."
            })
        # Then check if we have analysis data from the session (from uploaded image)
        elif "crop_analysis" in st.session_state and not any("Identified Crops" in str(m.get("content", "")) for m in api_messages[:3]):
            # Extract the relevant information
            analysis_data = st.session_state["crop_analysis"]
            if "result" in analysis_data and analysis_data["result"]:
                result = analysis_data["result"]
                context = "You are a crop disease identification expert. The user has uploaded an image that has been analyzed. "
                
                # Add crop information
                if "crop" in result and "suggestions" in result["crop"] and result["crop"]["suggestions"]:
                    crops = result["crop"]["suggestions"]
                    crop_names = [f"{c['name']} ({c['scientific_name']})" for c in crops if "name" in c and "scientific_name" in c]
                    context += f"The image shows {', '.join(crop_names)}. "
                
                # Add disease information
                if "disease" in result and "suggestions" in result["disease"] and result["disease"]["suggestions"]:
                    diseases = result["disease"]["suggestions"]
                    disease_names = [d["name"] for d in diseases if "name" in d]
                    context += f"The plant shows signs of {', '.join(disease_names)}. "
                
                context += "Provide detailed advice on cultivation, disease management, and best practices for this crop."
                
                api_messages.insert(1, {
                    "role": "system",
                    "content": context
                })
        
        # Show a spinner while waiting for API response
        with st.spinner("DeepSeek AI is analyzing your request..."):
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8501",
                    "X-Title": "Crop Disease ChatBot",
                },
                extra_body={},
                model="deepseek/deepseek-chat:free",
                messages=api_messages,
            )
            bot_reply = completion.choices[0].message.content
            
            # Add the response to chat history
            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
            
    except Exception as e:
        st.session_state["messages"].append({"role": "assistant", "content": f"Error: {str(e)}"})
        st.error(f"Error: {str(e)}")

# Add file uploader to the sidebar
with st.sidebar:
    st.subheader("Upload a Crop Image for Analysis")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"], key="sidebar_image")
    
    if uploaded_file:
        # Show the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        # Add analyze button
        if st.button("Analyze Crop", key="analyze_btn"):
            image_bytes = uploaded_file.read()
            
            # Create a placeholder for the analysis results
            analysis_placeholder = st.empty()
            analysis_placeholder.info("Analyzing your crop image...")
            
            # Use the CropAnalyzer to analyze the image
            analyzer = CropAnalyzer()
            analysis_results = analyzer.analyze_image_bytes(image_bytes)
            
            if analysis_results["success"]:
                # Get the formatted summary
                crop_summary = analysis_results["summary"]
                analysis_placeholder.success("Analysis complete!")
                
                # Add the message to the chat
                st.session_state["messages"].append({
                    "role": "user",
                    "content": f"[Image uploaded: {uploaded_file.name}]",
                    "image_base64": base64.b64encode(image_bytes).decode()
                })
                
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"I've analyzed your crop image and here are the results:\n\n{crop_summary}\n\nWould you like more specific information about these crops or advice on cultivation and disease management?"
                })
                
                # Save the analysis data in session state for further reference
                st.session_state["crop_analysis"] = analysis_results["api_response"]
                
                # Set flag to indicate message was sent
                st.session_state["message_sent"] = True
                
                # Rerun to update the UI
                st.rerun()
            else:
                # If analysis failed, show error message
                error_msg = analysis_results.get("error", "Unknown error occurred during analysis")
                analysis_placeholder.error(f"Analysis failed: {error_msg}")

# Handle text input using the new Streamlit chat_input API
prompt = st.chat_input("Type your message here...")

if prompt:
    # Add user message to chat history
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    # Set flag to indicate message was sent
    st.session_state["message_sent"] = True
    
    # Process the message with API
    process_with_api()
    
    # Rerun to update the UI
    st.rerun()

# Add helpful information in the sidebar
with st.sidebar:
    st.markdown("---")
    st.subheader("About Crop Disease Identifier")
    st.info("""
    This application uses:
    1. KindWise API for crop and disease identification
    2. DeepSeek AI for comprehensive analysis and advice
    
    You can upload crop images for analysis or simply chat about crops and plant diseases.
    """)
    
    st.markdown("---")
    st.caption("© 2025 Crop Disease Identifier")
