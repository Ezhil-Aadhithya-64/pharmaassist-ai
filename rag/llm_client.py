# from openai import OpenAI  # Or any client for LLaMA-3.1 via API


# def llm(prompt: str):
#     try:
#         completion = client.chat.completions.create(
#             model="meta-llama/Llama-3.1-8B-Instruct:novita",
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=200
#         )
#         return completion.choices[0].message["content"]
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return "Error generating response"

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from config import HF_TOKEN
# Load API token from .env
load_dotenv()
token = os.getenv("HF_TOKEN")

# if not token:
#     raise ValueError("HF_TOKEN not found in .env")

# Initialize HuggingFace Inference client
client = InferenceClient(api_key=HF_TOKEN)

def llm(prompt: str):
    """
    Generate a response using Hugging Face LLaMA model via Inference API.
    """
    try:
        completion = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct:novita",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        # Return the generated content
        return completion.choices[0].message["content"]
    except Exception as e:
        print("LLM ERROR:", e)
        return "Error generating response"