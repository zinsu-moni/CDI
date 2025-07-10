"""
Crop Analysis API Module
-----------------------
This module provides a way for the chatbot to access the DeepLeaf crop identification API
without needing to use the GUI application.
"""

import os
import json
import base64
import requests
from PIL import Image
import io
import tempfile

class CropAnalyzer:
    """
    A class for analyzing crop images using the KindWise API and returning
    structured results for the chatbot.
    """
    
    def __init__(self):
        # API Details - Using DeepLeaf API
        self.api_url = "https://api.deepleaf.io/analyze"
        self.api_key = "feed_the_world_bLLeZuQkUdTXxs13RpEWrYzzx05AIHOjHSrhItNIsbY"
    
    def analyze_image_bytes(self, image_bytes):
        """
        Analyze crop image from raw bytes
        
        Args:
            image_bytes: Raw image bytes (from memory)
        
        Returns:
            dict: Analysis results and formatted summary
        """
        try:
            # Convert bytes to image to ensure it's valid
            try:
                image = Image.open(io.BytesIO(image_bytes))
                # Resize and convert image to reduce size and ensure compatibility
                image = image.convert('RGB')
                
                # Resize if image is too large (max dimension 1024px)
                max_size = 1024
                if max(image.size) > max_size:
                    ratio = max_size / max(image.size)
                    new_size = tuple(int(dim * ratio) for dim in image.size)
                    image = image.resize(new_size, Image.LANCZOS)
                
                # Convert back to bytes (JPEG format)
                output_buffer = io.BytesIO()
                image.save(output_buffer, format='JPEG', quality=95)
                image_bytes = output_buffer.getvalue()
            except Exception as img_err:
                return {
                    "success": False,
                    "error": f"Error processing image: {str(img_err)}",
                    "api_response": None
                }
            
            # Encode the image bytes to base64
            encoded_string = base64.b64encode(image_bytes).decode('utf-8')
            
            # Make the API request using DeepLeaf format
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'image': encoded_string
            }
            
            print(f"Sending request to {self.api_url} with auth token")
            
            # Call the API
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            # Check response
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Generate a summary for the chatbot
                summary = self.generate_summary(data)
                
                # Return both the raw data and formatted summary
                return {
                    "success": True,
                    "api_response": data,
                    "summary": summary
                }
            else:
                error_detail = "Unknown error"
                try:
                    error_detail = response.json()
                except:
                    try:
                        error_detail = response.text
                    except:
                        error_detail = f"Status code: {response.status_code}"
                
                print(f"API Error: {error_detail}")
                
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}: {error_detail}",
                    "api_response": error_detail
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "api_response": None
            }
    
    def analyze_image_file(self, image_path):
        """
        Analyze crop image from a file path
        
        Args:
            image_path: Path to the image file
        
        Returns:
            dict: Analysis results and formatted summary
        """
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
            
            return self.analyze_image_bytes(image_bytes)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading image file: {str(e)}",
                "api_response": None
            }
    
    def generate_summary(self, data):
        """
        Generate a human-readable summary from the DeepLeaf API response
        
        Args:
            data: The API response JSON
        
        Returns:
            str: Formatted summary
        """
        summary = "Crop Analysis Results:\n\n"
        
        try:
            # Print the raw data for debugging
            print("API Response Structure:", json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
            
            # Handle DeepLeaf API response format
            if 'analysis' in data and data['analysis']:
                analysis_data = data['analysis']
                
                # Add crop identification info
                if 'plant_species' in analysis_data and analysis_data['plant_species']:
                    crops = analysis_data['plant_species']
                    if crops:
                        summary += "Identified Crops:\n"
                        for crop in crops:
                            crop_name = crop.get('common_name', 'Unknown')
                            scientific_name = crop.get('scientific_name', '')
                            confidence = crop.get('confidence', 0) * 100
                            summary += f"- {crop_name} ({scientific_name}): {confidence:.2f}% confidence\n"
                    else:
                        summary += "No crops identified.\n"
                
                # Add disease information if available
                if 'diseases' in analysis_data and analysis_data['diseases']:
                    diseases = analysis_data['diseases']
                    if diseases:
                        summary += "\nPlant Health Conditions:\n"
                        for condition in diseases:
                            condition_name = condition.get('name', 'Unknown')
                            confidence = condition.get('confidence', 0) * 100
                            summary += f"- {condition_name}: {confidence:.2f}% confidence\n"
                            
                            # Add treatment recommendations if available
                            if 'treatments' in condition and condition['treatments']:
                                summary += "  Recommended treatments:\n"
                                for treatment in condition['treatments']:
                                    summary += f"  • {treatment}\n"
                    else:
                        summary += "\nNo diseases detected. The plant appears healthy.\n"
                        
                # Add general health assessment if available
                if 'health_assessment' in analysis_data:
                    health = analysis_data['health_assessment']
                    summary += f"\nOverall Plant Health: {health.get('status', 'Unknown')}\n"
                    if 'recommendations' in health and health['recommendations']:
                        summary += "General Recommendations:\n"
                        for rec in health['recommendations']:
                            summary += f"- {rec}\n"
            
            # Check for alternative format - results array
            elif 'results' in data:
                results = data['results']
                
                # Check if it's a list of results
                if isinstance(results, list) and results:
                    result = results[0]  # Take the first result
                    
                    # Parse plant info
                    if 'species' in result:
                        species = result['species']
                        summary += "Identified Crop:\n"
                        common_name = species.get('common_name', 'Unknown')
                        scientific_name = species.get('scientific_name', '')
                        confidence = species.get('probability', 0) * 100
                        summary += f"- {common_name} ({scientific_name}): {confidence:.2f}% confidence\n"
                    
                    # Parse disease info
                    if 'diseases' in result and result['diseases']:
                        diseases = result['diseases']
                        summary += "\nPlant Health Conditions:\n"
                        for disease in diseases:
                            name = disease.get('name', 'Unknown condition')
                            confidence = disease.get('probability', 0) * 100
                            summary += f"- {name}: {confidence:.2f}% confidence\n"
                            
                            # Add details if available
                            if 'description' in disease:
                                summary += f"  Description: {disease['description']}\n"
                            
                            if 'treatment' in disease:
                                summary += "  Recommended treatment:\n"
                                summary += f"  • {disease['treatment']}\n"
                
                # If it's a direct object not in a list
                elif isinstance(results, dict):
                    # Parse plant info
                    if 'species' in results:
                        species = results['species']
                        summary += "Identified Crop:\n"
                        common_name = species.get('common_name', 'Unknown')
                        scientific_name = species.get('scientific_name', '')
                        confidence = species.get('probability', 0) * 100
                        summary += f"- {common_name} ({scientific_name}): {confidence:.2f}% confidence\n"
                    
                    # Parse disease info
                    if 'diseases' in results and results['diseases']:
                        diseases = results['diseases']
                        summary += "\nPlant Health Conditions:\n"
                        for disease in diseases:
                            name = disease.get('name', 'Unknown condition')
                            confidence = disease.get('probability', 0) * 100
                            summary += f"- {name}: {confidence:.2f}% confidence\n"
            else:
                # Fallback for unexpected response format
                summary += "Unable to parse crop identification results.\n"
                summary += f"Raw response available for debugging: {str(data)[:200]}...\n"
                
            return summary
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            return f"{summary}\nError parsing results: {str(e)}\n\nTrace: {traceback_str}\n"

# Function to save an image to a temporary file and return the path
def save_temp_image(image_bytes):
    """Save image bytes to a temporary file and return the path"""
    try:
        # Create a temporary file with .jpg extension
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)  # Close the file descriptor
        
        # Save the image to the temporary file
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)
            
        return temp_path
    except Exception as e:
        print(f"Error saving temporary image: {str(e)}")
        return None

# Simple test function
if __name__ == "__main__":
    # Test with a local file if provided as an argument
    import sys
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        analyzer = CropAnalyzer()
        results = analyzer.analyze_image_file(image_path)
        print(results["summary"])
        print("\nAPI Response:", json.dumps(results["api_response"], indent=2))
    else:
        print("Please provide an image path as an argument to test.")
