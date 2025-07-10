"""
Helper script to launch the chatbot with streamlit using proper arguments.
This avoids issues with running the chatbot directly with Python.
"""

import os
import sys
import subprocess
import shutil
import argparse

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Launch Crop Disease Chatbot')
    parser.add_argument('--analysis-data', type=str, help='Path to the crop analysis data JSON file')
    parser.add_argument('--image-path', type=str, help='Path to the analyzed crop image')
    args = parser.parse_args()
    
    # Get the path to the chatbot script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chatbot_path = os.path.join(script_dir, "CDI_CHAT_BOT_new.py")
    
    # Check if streamlit is installed
    streamlit_path = shutil.which("streamlit")
    
    cmd = []
    if streamlit_path:
        cmd = [streamlit_path, "run", chatbot_path]
    else:
        cmd = [sys.executable, "-m", "streamlit", "run", chatbot_path]
    
    # Add arguments if provided
    if args.analysis_data or args.image_path:
        cmd.append("--")
        
        if args.analysis_data:
            cmd.extend(["--analysis-data", args.analysis_data])
        
        if args.image_path:
            cmd.extend(["--image-path", args.image_path])
    
    print(f"Launching chatbot with command: {' '.join(cmd)}")
    
    try:
        # Launch the process
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching chatbot: {str(e)}")
        # Try to install streamlit if it might be missing
        if "No module named 'streamlit'" in str(e):
            print("Attempting to install Streamlit...")
            subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"], check=True)
            print("Streamlit installed. Please try running the application again.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
