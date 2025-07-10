import subprocess
import sys
import os

def main():
    """
    Main entry point to run the Crop Disease Identifier application
    """
    print("Starting Crop Disease Identifier...")
    
    # Get the absolute path to the test.py script
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.py")
    
    # Run the application
    try:
        subprocess.run([sys.executable, script_path])
    except Exception as e:
        print(f"Error running the application: {str(e)}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
