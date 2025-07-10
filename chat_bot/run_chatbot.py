"""
This is a utility script to easily launch the chatbot application
from the command line with proper streamlit configuration.
"""

import os
import sys
import subprocess
import webbrowser
import time

def main():
    """Launch the CDI Chatbot application"""
    print("=" * 50)
    print("Launching Crop Disease Identifier ChatBot")
    print("=" * 50)
    
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the chatbot script
    chatbot_script = os.path.join(script_dir, "CDI_CHAT_BOT.py")
    
    # Command to run
    cmd = ["streamlit", "run", chatbot_script]
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        cmd.append("--")
        cmd.extend(sys.argv[1:])
    
    try:
        # Start the streamlit process
        process = subprocess.Popen(cmd)
        
        # Wait a moment for the server to start
        print("Starting server...")
        time.sleep(2)
        
        # Open the browser
        webbrowser.open("http://localhost:8501")
        
        # Wait for the process to finish
        process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Try with python -m streamlit if direct streamlit command fails
        try:
            cmd = [sys.executable, "-m", "streamlit", "run", chatbot_script]
            if len(sys.argv) > 1:
                cmd.append("--")
                cmd.extend(sys.argv[1:])
                
            print("Trying alternative method...")
            process = subprocess.Popen(cmd)
            time.sleep(2)
            webbrowser.open("http://localhost:8501")
            process.wait()
        except Exception as e2:
            print(f"Alternative method failed: {str(e2)}")
            print("\nTo manually start the chatbot, run:")
            print(f"streamlit run {chatbot_script}")

if __name__ == "__main__":
    main()
