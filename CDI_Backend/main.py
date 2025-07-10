import os
import sys
import subprocess
import shutil

def main():
    """
    Main entry point for the Crop Disease Identifier (CDI) application suite
    """
    print("=" * 50)
    print("Crop Disease Identifier (CDI) Application Suite")
    print("=" * 50)
    print("\nPlease choose an option:")
    print("1. Launch ChatBot (Recommended)")
    print("2. Launch Crop Identifier App")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(base_dir)
    
    if choice == "1":
        # Run the ChatBot with FastAPI instead of Streamlit
        launcher_path = os.path.join(parent_dir, "chat_bot", "launch_fastapi.py")
        try:
            print("\nLaunching ChatBot with FastAPI...")
            # Use our FastAPI launcher script
            subprocess.run([sys.executable, launcher_path])
            print("ChatBot launched successfully! Please wait for the browser window to open.")
        except Exception as e:
            print(f"Error launching ChatBot: {str(e)}")
            print("\nTo run the ChatBot manually, execute the following command:")
            print(f"python {os.path.join(parent_dir, 'chat_bot', 'launch_fastapi.py')}")
    
    elif choice == "2":
        # Run the Crop Identifier app
        app_path = os.path.join(base_dir, "test.py")
        try:
            # Check if we are running the tkinter app directly
            print("\nLaunching Crop Identifier App...")
            subprocess.run([sys.executable, app_path], check=True)
        except Exception as e:
            print(f"Error launching Crop Identifier App: {str(e)}")
    
    elif choice == "3":
        print("Exiting application. Goodbye!")
        sys.exit(0)
    
    else:
        print("Invalid choice. Please run again and select a valid option.")
        
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
