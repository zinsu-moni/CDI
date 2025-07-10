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

# Only use streamlit functionality if running via streamlit
if "streamlit" in sys.modules:
    st.set_page_config(page_title="ChatBot", layout="centered")
    st.title("Crop Disease ChatBot")
    
    # Initialize the flag for clearing inputs if not present
    if "clear_inputs" not in st.session_state:
        st.session_state["clear_inputs"] = False
    
    # Initialize a place for storing current input that will be reset on form submission
    if "current_message" not in st.session_state:
        st.session_state["current_message"] = ""
        
    # Create a key for the input field that will be regenerated when we need to clear the input
    if "input_key" not in st.session_state:
        st.session_state["input_key"] = "input_" + str(hash(time.time()))
    
    # Initialize flag for tracking if we're awaiting symptom input from user
    if "awaiting_symptoms" not in st.session_state:
        st.session_state["awaiting_symptoms"] = False
        
    # Check if we need to clear inputs (this happens after a message is sent)
    if st.session_state["clear_inputs"]:
        # Generate a new key for the input field to force it to clear
        st.session_state["input_key"] = "input_" + str(hash(time.time()))
        st.session_state["current_message"] = ""
        st.session_state["clear_inputs"] = False
else:
    # If not running with streamlit, print a helpful message
    print("This script is designed to be run with Streamlit.")
    print("Please run it using: streamlit run CDI_CHAT_BOT.py")
    sys.exit(1)

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

# Initialize chat history in session state
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

# Display chat history
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
        if msg.get("image_base64"):
            st.image(base64.b64decode(msg["image_base64"]), caption="Uploaded Image", use_container_width=True)
    elif msg["role"] == "assistant":
        st.markdown(f"**DCI_Bot:** {msg['content']}")

# Function to handle API processing with a status indicator
def process_with_api():
    try:
        # Show a spinner while processing with the API
        with st.spinner("Processing your request with DeepSeek AI..."):
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key="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",
            )
            # Prepare messages for the API (remove image_base64, only send text)
            api_messages = [
                {k: v for k, v in m.items() if k != "image_base64"} for m in st.session_state["messages"][-10:]
            ]
        
            # Check if we're in symptoms collection mode and the user just provided symptoms
            if st.session_state.get("awaiting_symptoms", False) and len(api_messages) >= 2:
                # The last message should be the user's symptoms
                user_symptoms = api_messages[-1].get("content", "") if api_messages[-1]["role"] == "user" else ""
                
                if user_symptoms and "crop_analysis" in st.session_state:
                    # Add special system prompt for symptom analysis
                    analysis_data = st.session_state["crop_analysis"]
                    symptom_prompt = (
                        "You are an agricultural expert and plant pathologist. "
                        "The user has provided both an image of their crop and a description of symptoms. "
                        f"Based on the image analysis and the user's description of symptoms: '{user_symptoms}', "
                        "provide a detailed diagnosis and treatment plan. "
                        "Include both preventative measures and remedies if applicable. "
                        "Be specific and consider both organic and conventional treatment options."
                    )
                    
                    # Insert the symptom prompt at the beginning
                    api_messages.insert(0, {
                        "role": "system",
                        "content": symptom_prompt
                    })
                    
                    # Clear the awaiting symptoms flag
                    st.session_state["awaiting_symptoms"] = False
            
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
        st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
    except Exception as e:
        st.session_state["messages"].append({"role": "assistant", "content": f"Error: {str(e)}"})

# Define the function to handle message submission
def submit_message():
    if "current_input" in st.session_state and st.session_state.current_input:
        # Add user message to chat history
        st.session_state["messages"].append({"role": "user", "content": st.session_state.current_input})
        
        # Process with API
        process_with_api()
        
        # Clear input
        st.session_state["current_input"] = ""
        st.rerun()

# If analyzed image is already loaded, display it
if analyzed_image and 'displayed_analysis_image' not in st.session_state:
    st.image(analyzed_image, caption="Analyzed Crop Image", use_container_width=True)
    st.session_state['displayed_analysis_image'] = True

# Define a callback to handle input changes
def handle_input_change():
    # Store the current value from the dynamic key in our session state
    input_key = st.session_state["input_key"]
    if input_key in st.session_state and st.session_state[input_key]:
        st.session_state["current_message"] = st.session_state[input_key]

# User input and image upload
col1, col2 = st.columns([4, 1])
with col1:
    # Show different prompt if we're waiting for symptoms
    if st.session_state.get("awaiting_symptoms", False):
        placeholder_text = "Please describe the symptoms you observe on your plant..."
        input_label = "Describe Symptoms:"
    else:
        placeholder_text = "Type your message here..."
        input_label = "Type your message:"
    
    # Use the dynamic key for the text input to ensure it resets when needed
    user_input = st.text_input(
        input_label, 
        key=st.session_state["input_key"], 
        on_change=handle_input_change,
        placeholder=placeholder_text
    )
with col2:
    # For the file uploader, we won't try to reset it directly
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], key="file_uploader")

# Add instructions for the user
if st.session_state.get("awaiting_symptoms", False):
    st.caption("💡 Please describe any symptoms you observe on your crop to help us provide a more accurate analysis.")
    # Add an example collapsible section
    with st.expander("See examples of helpful symptom descriptions"):
        st.markdown("""
        **Good symptom descriptions include:**
        - "Yellow spots on leaves that start small and grow larger"
        - "White powdery substance on the underside of leaves"
        - "Leaves are curling and turning brown at the edges"
        - "Stunted growth with wilting despite regular watering"
        - "Black spots on fruit with concentric rings"
        
        **Include information about:**
        - Which parts of the plant are affected (leaves, stems, roots, fruit)
        - When symptoms first appeared
        - How quickly symptoms are progressing
        - Any treatments you've already tried
        - Environmental conditions (weather, watering schedule, etc.)
        """)

# Use our current_message state to track the input
if user_input:
    st.session_state["current_message"] = user_input

# Send button handler
if st.button("Send"):
    has_content = False
    
    # Process text input
    if st.session_state["current_message"]:
        has_content = True
        # Get the message from our stored value
        message_to_send = st.session_state["current_message"]
        st.session_state["messages"].append({"role": "user", "content": message_to_send})
        # Reset our stored value by flagging for input clearing on next render
        st.session_state["clear_inputs"] = True
    
    # Process image upload (only if there is an image)
    elif uploaded_file:
        has_content = True
        image_bytes = uploaded_file.read()
        b64_image = base64.b64encode(image_bytes).decode()
        
        # Display a status message while analyzing
        with st.spinner("Analyzing your crop image with our professional identification API..."):
            # Use the CropAnalyzer to analyze the image
            analyzer = CropAnalyzer()
            analysis_results = analyzer.analyze_image_bytes(image_bytes)
            
            if analysis_results["success"]:
                # Get the formatted summary
                crop_summary = analysis_results["summary"]
                
                # Check if we have confident identifications
                has_high_confidence = False
                api_response = analysis_results["api_response"]
                
                # Check confidence level in the API response
                if ('result' in api_response and 
                    'crop' in api_response['result'] and 
                    'suggestions' in api_response['result']['crop']):
                    
                    suggestions = api_response['result']['crop']['suggestions']
                    if suggestions:
                        # Check if the top suggestion has at least 50% confidence
                        top_confidence = suggestions[0].get('probability', 0) * 100
                        has_high_confidence = top_confidence >= 50.0
                
                # Save the analysis data in session state for further reference
                st.session_state["crop_analysis"] = analysis_results["api_response"]
                
                # Add the message to the chat
                if has_high_confidence:
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": f"I've analyzed your crop image and here are the results:\n\n{crop_summary}\n\nWould you like more specific information about these crops or advice on cultivation and disease management?"
                    })
                else:
                    # If confidence is low, ask for symptoms
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": f"I've analyzed your crop image, but I'm not entirely confident about the identification:\n\n{crop_summary}\n\nCould you please describe any symptoms you observe? For example:\n- What color changes do you see on the leaves?\n- Are there spots, wilting, or unusual growth?\n- When did you first notice these issues?\n- What part of the plant is affected?\n\nThis will help me provide a more accurate analysis."
                    })
                    
                    # Set a flag to indicate we're in symptom collection mode
                    st.session_state["awaiting_symptoms"] = True
                    
            else:
                # If analysis failed, show error message and ask for symptoms
                error_msg = analysis_results.get("error", "Unknown error occurred during analysis")
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": f"I encountered an issue while analyzing your image: {error_msg}\n\nInstead, could you please describe the symptoms you're observing on your crop? Details about leaf color, spots, wilting, or any unusual patterns will help me provide a better diagnosis."
                })
                
                # Set a flag to indicate we're in symptom collection mode
                st.session_state["awaiting_symptoms"] = True
        
        # Add the user message with the image
        st.session_state["messages"].append({
            "role": "user",
            "content": f"[Image uploaded: {uploaded_file.name}]",
            "image_base64": b64_image
        })
    
    # Only proceed with API call if there's actual content to process
    if has_content:
        # Process with API (only once)
        process_with_api()
        
        # Set a flag to indicate that we should clear inputs on next render
        st.session_state["clear_inputs"] = True
        
        # Rerun to update the UI
        st.rerun()
    else:
        # If Send button was clicked but no message or image, show a message to the user
        st.warning("Please enter a message or upload an image before sending.")
