import base64
from mimetypes import guess_type
from openai import AzureOpenAI
import json
import time
from icecream import ic
import streamlit as st

try:
    import config_azure as config
except ImportError:
    class Config:
        AZURE_ENDPOINT = 'https://redcheckllm.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview'
        AZURE_API_KEY = st.session_state.token
    config = Config()

# Load layouts.json
with open("streamlit/src/layouts.json", "r") as f:
    layouts = json.load(f)

# Decorator to measure execution time of a function
def measure_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time_seconds = round(end_time - start_time, 2)

        ic(func.__name__)
        ic(execution_time_seconds)
        
        return result
    return wrapper

def costs(metadata, input_rate=2.5, cached_rate=1.25, output_rate=10.0):
    """
    Calculate the costs based on the metadata provided.
    :param metadata: Dictionary containing token usage details.
    :param input_rate: Cost per million input tokens.
    :param cached_rate: Cost per million cached tokens.
    :param output_rate: Cost per million output tokens.
    :return: Dictionary with cost breakdown.
    """

    prompt_tokens = metadata.get("prompt_tokens", 0)
    cached_tokens = metadata.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    completion_tokens = metadata.get("completion_tokens", 0)

    non_cached_prompt_tokens = max(prompt_tokens - cached_tokens, 0)

    input_cost = non_cached_prompt_tokens / 1_000_000 * input_rate
    cached_input_cost = cached_tokens / 1_000_000 * cached_rate
    output_cost = completion_tokens / 1_000_000 * output_rate

    total_cost = input_cost + cached_input_cost + output_cost

    return {
        "input_cost": round(input_cost, 3),
        "cached_input_cost": round(cached_input_cost, 3),
        "output_cost": round(output_cost, 3),
        "total_cost": round(total_cost, 3)
    }

# Function to encode a local image into a data URL 
def local_image_to_data_url(image_path):
    # Guess the MIME type based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_encoded_data}"


@measure_time
def analyze_image(image_path: str, tipo_exame: str, prompt: str) -> dict:
    # Load API configuration from config.py
    endpoint = config.AZURE_ENDPOINT  # e.g., "https://redcheckllm.openai.azure.com/"
    deployment = "gpt-4o"
    subscription_key = config.AZURE_API_KEY  # Your key

    # Initialize the Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2024-05-01-preview",
    )

    # Read and encode image using the helper function
    try:
        data_url = local_image_to_data_url(image_path)
    except Exception as e:
        return {"error": f"Failed to read and encode image: {e}"}

    # Prepare chat prompt with system message and user message containing the image data.
    system_message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": (prompt)
            }
        ]
    }

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            }
        ]
    }
    assistant_placeholder = {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": f"Isto se trata de um exame do tipo {tipo_exame}."
            }
        ]
    }

    messages = [system_message, user_message, assistant_placeholder]

    # Call the service to generate the completion
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=800,
        temperature=0.2,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )

    # Parse the output. It is assumed the response JSON has a "choices" list with a "message" field.
    result_json = completion.to_json()
    result_dict = json.loads(result_json)
    try:
        output_text = result_dict["choices"][0]["message"]["content"]
    except (IndexError, KeyError):
        output_text = ""

    # Also return metadata (e.g., token usage) if available.
    metadata = result_dict.get("usage", {})
    costs_values = costs(metadata)

    return {"output": output_text, "metadata": metadata, "costs": costs_values}


@measure_time
def synthesize_medical_report(output_texts: list, tipo_exame: str, prompt: str) -> dict:
    estrutura = layouts[tipo_exame]
    
    # Concatena todas as descrições clínicas
    combined_text = "\n\n".join(output_texts)

    # Define as mensagens para o chat, incluindo o prompt detalhado e o texto agregado
    system_message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": (
                    f"{prompt}\n\n"
                    f"{estrutura}\n\n"
                    "3. Indique se o exame é 'Normal', 'Anormal' ou 'Não Avaliável' na chave diagnosis.\n"
                    "4. Se for 'Anormal', inclua na chave diagnosis_description as possíveis hipóteses clínicas associadas aos achados (como retinopatia diabética, edema de papila, oclusão venosa, etc.).\n\n"
                    "Retorne sua resposta no seguinte formato JSON:\n\n"
                    "{\n  \"description\": \"[insira o laudo formatado conforme acima]\",\n  \"diagnosis\": \"[normal | abnormal | non_available]\",\n  \"diagnosis_description\": \"[preencha apenas se o diagnóstico for 'abnormal']\"\n}"
                )
            }
        ]
    }

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": combined_text
            }
        ]
    }

    messages = [system_message, user_message]

    # Configuração da API
    endpoint = config.AZURE_ENDPOINT
    deployment = "gpt-4o"
    subscription_key = config.AZURE_API_KEY

    # Inicializa o cliente Azure OpenAI
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2024-05-01-preview",
    )

    # Chama a API com as mensagens preparadas
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=800,
        temperature=0.2,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False,
        response_format={"type": "json_object"}
    )

    # Processa a resposta
    result_json = completion.to_json()
    result_dict = json.loads(result_json)
    
    # Metadata
    metadata = result_dict.get("usage", {})
    costs_values = costs(metadata)

    try:
        output_text = result_dict["choices"][0]["message"]["content"]
    except (IndexError, KeyError):
        output_text = ""

    # Tenta converter a resposta para um dicionário JSON
    try:
        final_result = json.loads(output_text)
    except json.JSONDecodeError:
        final_result = {"error": "Falha ao interpretar a resposta como JSON.", "raw_response": output_text}

    return {"output": final_result, "metadata": metadata, "costs": costs_values}


if __name__ == "__main__":
    # Example usage:
    image_path = "samples/sample.jpg"
    image_path_2 = "samples/sample_2.jpg"
    result = analyze_image(image_path, tipo_exame="oct_macula")
    result_2 = analyze_image(image_path_2, tipo_exame="oct_macula")
    synthesis = synthesize_medical_report([result["output"], result_2["output"]], tipo_exame="oct_macula")
    if "error" in result:
        ic(result["error"])
    else:
        sum_costs = {key: result["costs"].get(key, 0) + result_2["costs"].get(key, 0) for key in result["costs"]}
        ic(sum_costs)
        ic(synthesis["output"])
        ic(synthesis["metadata"])
        ic(synthesis["costs"])