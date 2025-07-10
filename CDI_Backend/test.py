import os
import tkinter as tk
from tkinter import filedialog, Label, Button, Text, Scrollbar, Frame, messagebox
from PIL import Image, ImageTk
import requests
import io
import base64
import json
import subprocess
import sys
import shutil

class CropIdentifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Crop Identifier")
        self.root.geometry("800x600")
        
        # API Details
        self.api_url = "https://crop.kindwise.com/api/v1/identification"
        self.api_key = "u12lFbhGXOPacNJgi4pqK2scNsm34OryIiw99IIPJLKzjgntD5"  # Your API key
        
        # Create UI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Image selection
        self.select_btn = Button(main_frame, text="Select Image", command=self.select_image)
        self.select_btn.pack(pady=10)
        
        # Image preview
        self.image_frame = Frame(main_frame, width=400, height=300, bg="lightgray")
        self.image_frame.pack(pady=10)
        self.image_label = Label(self.image_frame)
        self.image_label.pack(expand=True)
        
        # Analyze button
        self.analyze_btn = Button(main_frame, text="Analyze Crop", command=self.analyze_image, state=tk.DISABLED)
        self.analyze_btn.pack(pady=10)
        
        # Send to ChatBot button (initially disabled)
        self.chatbot_btn = Button(main_frame, text="Send to ChatBot for Analysis", 
                                 command=self.send_to_chatbot, state=tk.DISABLED)
        self.chatbot_btn.pack(pady=10)
        
        # Results area
        result_frame = Frame(main_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = Text(result_frame, height=10, width=50)
        self.result_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        self.result_text.insert(tk.END, "Results will appear here...\n")
        self.result_text.config(state=tk.DISABLED)
        
        # Store API results for later use
        self.api_results = None
    
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")]
        )
        
        if file_path:
            self.image_path = file_path
            self.display_image(file_path)
            self.analyze_btn['state'] = tk.NORMAL
            
            # Clear previous results
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.config(state=tk.DISABLED)
    
    def display_image(self, file_path):
        # Display the selected image
        img = Image.open(file_path)
        
        # Resize image to fit display
        max_size = (380, 280)
        img.thumbnail(max_size, Image.LANCZOS)
        
        photo = ImageTk.PhotoImage(img)
        self.image_label.config(image=photo)
        self.image_label.image = photo  # Keep a reference to prevent garbage collection
        
    def analyze_image(self):
        if not hasattr(self, 'image_path'):
            return
        
        if not self.api_key:
            self.update_result("Error: API Key not provided. Please set your API key in the code.")
            return
        
        self.update_result("Analyzing image...\n")
        
        try:
            # Prepare the image for API
            with open(self.image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare the API request
            headers = {
                'Content-Type': 'application/json',
                'Api-Key': self.api_key
            }
            
            payload = {
                'images': [encoded_string],
                'similar_images': True
                # Removed 'details': 'full' as it's not supported by the API
            }
            
            # Make the API call
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            # Process the response
            if response.status_code in [200, 201]:  # Both 200 and 201 indicate success
                data = response.json()
                self.display_results(data)
            else:
                self.update_result(f"Error: API returned status code {response.status_code}\n")
                self.update_result(f"Response: {response.text}\n")
        
        except Exception as e:
            self.update_result(f"An error occurred: {str(e)}\n")
    
    def display_results(self, data):
        self.update_result("Analysis Complete!\n\n")
        
        try:
            # Store the API results for later use with chatbot
            self.api_results = data
            
            # Extract crop information from the KindWise API format
            if 'result' in data and data['result'] and 'crop' in data['result']:
                crop_data = data['result']['crop']
                if 'suggestions' in crop_data and crop_data['suggestions']:
                    self.update_result("=== IDENTIFIED CROPS ===\n")
                    # Display all crop suggestions with their probabilities
                    for i, crop in enumerate(crop_data['suggestions']):
                        crop_name = crop.get('name', 'Unknown')
                        scientific_name = crop.get('scientific_name', '')
                        confidence = crop.get('probability', 0) * 100  # Convert to percentage
                        
                        self.update_result(f"Crop {i+1}: {crop_name} ({scientific_name})\n")
                        self.update_result(f"Confidence: {confidence:.2f}%\n\n")
                else:
                    self.update_result("No crop suggestions returned.\n")
                
                # If there's disease information, display it too
                if 'disease' in data['result'] and 'suggestions' in data['result']['disease']:
                    disease_data = data['result']['disease']['suggestions']
                    if disease_data:
                        self.update_result("\n=== PLANT HEALTH ===\n")
                        for i, condition in enumerate(disease_data):
                            condition_name = condition.get('name', 'Unknown')
                            confidence = condition.get('probability', 0) * 100
                            self.update_result(f"Condition {i+1}: {condition_name} (Confidence: {confidence:.2f}%)\n")
            else:
                self.update_result("No crop identification results returned from the API.\n")
            
            # Include the access token for reference (might be needed for follow-up API calls)
            if 'access_token' in data:
                self.update_result(f"\nAccess Token: {data['access_token']}\n")
                
            # Enable the chatbot button now that we have results
            self.chatbot_btn['state'] = tk.NORMAL
                
            # For debugging, you can uncomment this section to see the full API response
            # self.update_result("\n--- Full API Response ---\n")
            # self.update_result(str(data))
        
        except Exception as e:
            self.update_result(f"Error parsing results: {str(e)}\n")
            self.update_result("\nDisplaying raw response:\n")
            self.update_result(str(data))
    
    def update_result(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, text)
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)
    
    def send_to_chatbot(self):
        if not self.api_results:
            messagebox.showerror("Error", "No analysis results available to send to the chatbot.")
            return
        
        try:
            # Create a formatted summary of the crop analysis to send to the chatbot
            crop_summary = "Crop Analysis Results:\n\n"
            
            if 'result' in self.api_results and self.api_results['result']:
                result_data = self.api_results['result']
                
                # Add crop identification info
                if 'crop' in result_data and 'suggestions' in result_data['crop']:
                    crop_suggestions = result_data['crop']['suggestions']
                    if crop_suggestions:
                        crop_summary += "Identified Crops:\n"
                        for i, crop in enumerate(crop_suggestions):
                            crop_name = crop.get('name', 'Unknown')
                            scientific_name = crop.get('scientific_name', '')
                            confidence = crop.get('probability', 0) * 100
                            crop_summary += f"- {crop_name} ({scientific_name}): {confidence:.2f}% confidence\n"
                
                # Add disease information if available
                if 'disease' in result_data and 'suggestions' in result_data['disease']:
                    disease_suggestions = result_data['disease']['suggestions']
                    if disease_suggestions:
                        crop_summary += "\nPlant Health Conditions:\n"
                        for i, condition in enumerate(disease_suggestions):
                            condition_name = condition.get('name', 'Unknown')
                            confidence = condition.get('probability', 0) * 100
                            crop_summary += f"- {condition_name}: {confidence:.2f}% confidence\n"
            
            # Save the crop data to a temporary file for the chatbot to access
            crop_data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crop_analysis_data.json")
            with open(crop_data_file, "w") as f:
                json.dump({
                    "crop_summary": crop_summary,
                    "raw_data": self.api_results
                }, f)
            
            # Save the image in a format the chatbot can access
            image_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyzed_image.jpg")
            img = Image.open(self.image_path)
            img.save(image_file_path, "JPEG")
            
            # Launch the chatbot with the analysis results
            self.update_result("\nLaunching ChatBot with analysis results...\n")
            
            # Get the absolute path to the chatbot launcher script
            launcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chat_bot", "launch_chatbot.py")
            
            # Launch the chatbot in a new process using our launcher script
            try:
                self.update_result("Launching ChatBot...\n")
                # Use the launcher script which handles streamlit properly
                subprocess.Popen([
                    sys.executable, launcher_path,
                    "--analysis-data", crop_data_file,
                    "--image-path", image_file_path
                ])
                self.update_result("ChatBot launched successfully! Please interact with it in the new window.\n")
            except Exception as e:
                self.update_result(f"Error launching ChatBot: {str(e)}\n")
                messagebox.showerror("Error", f"Could not launch ChatBot: {str(e)}")
                
        except Exception as e:
            self.update_result(f"Error preparing data for ChatBot: {str(e)}\n")
            messagebox.showerror("Error", f"Could not prepare data for ChatBot: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CropIdentifierApp(root)
    root.mainloop()