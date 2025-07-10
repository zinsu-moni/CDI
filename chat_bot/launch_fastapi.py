"""
Launcher script for the FastAPI server.
This replaces the Streamlit launcher with a FastAPI server launcher.
"""

import os
import sys
import subprocess
import webbrowser
import time

def main():
    """Launch the Crop Disease Identifier FastAPI server"""
    print("=" * 50)
    print("Launching Crop Disease Identifier FastAPI Server")
    print("=" * 50)
    
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the FastAPI script
    api_script = os.path.join(script_dir, "fast_api.py")
    
    try:
        # Check if uvicorn is installed
        try:
            subprocess.run([sys.executable, "-c", "import uvicorn"], check=True)
        except subprocess.CalledProcessError:
            print("Installing uvicorn...")
            subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi"], check=True)
            print("Uvicorn and FastAPI installed successfully.")
        
        # Start the FastAPI server
        print("\nStarting FastAPI server...")
        
        # Build the command
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "fast_api:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ]
        
        # Start the server process
        server_process = subprocess.Popen(
            cmd, 
            cwd=script_dir,  # Set working directory to the script directory
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the server to start
        print("Waiting for server to start...")
        time.sleep(2)
        
        # Open the browser
        print("Opening browser...")
        webbrowser.open("http://localhost:8000")
        
        print("\nServer running at http://localhost:8000")
        print("Press Ctrl+C to stop the server")
        
        # Keep running until interrupted
        try:
            while server_process.poll() is None:
                output = server_process.stdout.readline()
                if output:
                    print(output.strip())
        except KeyboardInterrupt:
            print("\nShutting down server...")
            server_process.terminate()
            server_process.wait()
            print("Server stopped.")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTo manually start the FastAPI server, run:")
        print(f"cd {script_dir}")
        print("uvicorn fast_api:app --reload")

if __name__ == "__main__":
    main()
