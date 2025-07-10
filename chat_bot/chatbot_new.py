import base64
from PIL import Image
import numpy as np
import io
from openai import OpenAI

class ChatBot:
    def __init__(self):
        # Updated system prompt to guide responses
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant for crop disease identification and advice. When responding about diseases, structure your answers with clear headings for Problem/Disease, Symptoms (as bullet points), and Treatment (as numbered steps). Use markdown formatting with ### for headings."}
        ]
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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",
        )

    def add_user_message(self, content, image_base64=None):
        msg = {"role": "user", "content": content}
        if image_base64:
            msg["image_base64"] = image_base64
        self.messages.append(msg)
        return self.messages

    def add_assistant_message(self, content):
        self.messages.append({"role": "assistant", "content": content})
        return self.messages

    def get_history(self):
        return self.messages

    def analyze_image(self, image_bytes):
        """Analyze an image using a pre-trained model and return disease prediction details"""
        # Convert bytes to image for analysis
        img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        img = img.resize((256, 256))
        img_array = np.array(img)

        # Simple mock classifier (replace with your ML model)
        green = np.mean(img_array[:, :, 1])
        red = np.mean(img_array[:, :, 0])
        yellowish = green > 100 and red > 100 and abs(green - red) < 30

        if yellowish:
            prediction = "Tomato Late Blight"
            symptoms = [
                "Dark, water-soaked spots on leaves, often with white fungal growth on the underside",
                "Brown, irregular lesions on stems and fruit",
                "Rapid spread in cool, wet conditions"
            ]
            treatments = [
                "Remove Infected Leaves: Prune and destroy affected plant parts to prevent spread",
                "Apply Fungicide: Use chlorothalonil or copper-based sprays (e.g., Bordeaux mixture)",
                "Improve Airflow: Space plants properly to reduce humidity around foliage",
                "Avoid Overhead Watering: Water at the base of plants to keep leaves dry",
                "Rotate Crops: Avoid planting tomatoes or related crops in the same spot next season"
            ]
        else:
            prediction = "Unknown Condition"
            symptoms = [
                "Image unclear or insufficient symptoms visible",
                "Early stage disease that's not yet identifiable",
                "Non-disease related stress (nutrient, water, environmental)"
            ]
            treatments = [
                "Monitor the Plant: Watch for developing symptoms",
                "Check Growing Conditions: Ensure proper watering, sunlight, and soil quality",
                "Consider Testing: If symptoms worsen, consider a soil or tissue test",
                "Consult an Expert: For accurate diagnosis, consult a local agricultural extension service"
            ]

        # Create structured analysis for display and for sending to DeepSeek
        analysis_for_ai = f"""Based on the image analysis, I've identified the following:
Disease: {prediction}

Symptoms detected:
- {symptoms[0]}
- {symptoms[1]}
- {symptoms[2]}

Recommended treatments:
1. {treatments[0]}
2. {treatments[1]}
3. {treatments[2]}
4. {treatments[3]}"""

        if len(treatments) > 4:
            analysis_for_ai += f"\n5. {treatments[4]}"

        # Create formatted response for display to user
        structured_response = f"""### **Problem: {prediction}**
- **Symptoms**:
  - {symptoms[0]}
  - {symptoms[1]}
  - {symptoms[2]}

### **Treatment**:
1. **{treatments[0].split(': ')[0]}**: {treatments[0].split(': ')[1]}
2. **{treatments[1].split(': ')[0]}**: {treatments[1].split(': ')[1]}
3. **{treatments[2].split(': ')[0]}**: {treatments[2].split(': ')[1]}
4. **{treatments[3].split(': ')[0]}**: {treatments[3].split(': ')[1]}"""

        if len(treatments) > 4:
            structured_response += f"\n5. **{treatments[4].split(': ')[0]}**: {treatments[4].split(': ')[1]}"

        return {
            "prediction": prediction,
            "analysis_for_ai": analysis_for_ai,  # This will be sent to DeepSeek
            "formatted_response": structured_response  # This can be shown directly to the user
        }

    def get_ai_response(self, user_question, image_analysis=None):
        """Get a response from the AI model based on image analysis and user question"""
        try:
            # Start with the system prompt
            api_messages = [self.messages[0]]  # System prompt

            # If there's image analysis, add it as assistant message first
            if image_analysis:
                api_messages.append({
                    "role": "assistant",
                    "content": image_analysis["analysis_for_ai"]
                })

            # Add the user's question
            api_messages.append({
                "role": "user",
                "content": user_question
            })

            # Add formatting reminder
            api_messages.append({
                "role": "system",
                "content": "Address the user's question about the identified disease. Maintain the structured format with markdown headings."
            })

            completion = self.client.chat.completions.create(
                extra_headers={
                    "X-Title": "Crop Disease ChatBot API",
                },
                extra_body={},
                model="deepseek/deepseek-chat:free",
                messages=api_messages,
            )

            bot_reply = completion.choices[0].message.content
            self.add_assistant_message(bot_reply)
            return bot_reply
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.add_assistant_message(error_message)
            return error_message
