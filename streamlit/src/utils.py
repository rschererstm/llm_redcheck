# src/utils.py

import openai
import os

# Example: If using Azure OpenAI, set up your credentials:
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-azure-openai-endpoint.openai.azure.com/")
openai.api_version = "2023-03-15-preview"
openai.api_key = os.getenv("AZURE_OPENAI_KEY", "your-azure-openai-key")

def generate_image_description(image_file, prompt, model_name):
    """
    Call your LLM to get a description. 
    For instance, you can pass in a "vision" prompt or the image bytes, 
    or do your own image -> text pipeline (depending on your approach).
    """
    # This is just a mock example using a ChatCompletion. Adjust to your real usage.
    # If you have an image -> text model, you might need a separate pipeline instead.
    system_message = "You are a helpful assistant specialized in medical imaging descriptions."
    user_message = f"Please describe the image in detail.\nCustom prompt: {prompt}"
    
    response = openai.ChatCompletion.create(
        engine=model_name,  # Azure deployment name of your model
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1
    )
    return response["choices"][0]["message"]["content"]

def generate_combined_report(description_right, description_left, reasoning_prompt, model_name):
    """
    Combine both descriptions into a single coherent report using a second model or prompt.
    """
    system_message = "You are a medical AI assistant that combines findings from two eye descriptions."
    user_message = f"""
    Right eye description:\n{description_right}

    Left eye description:\n{description_left}

    Using the prompt: {reasoning_prompt}

    Please produce a single medical report combining both.
    """

    response = openai.ChatCompletion.create(
        engine=model_name,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=0.1
    )
    return response["choices"][0]["message"]["content"]
