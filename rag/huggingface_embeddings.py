from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
from config import HF_TOKEN
# load_dotenv()
# token = os.getenv("HF_TOKEN")

# if not token:
#     raise ValueError("HF_TOKEN not found in .env")

client = InferenceClient(api_key=HF_TOKEN)

def get_embeddings(texts):
    """
    Input: a string or list of strings
    Output: list of embeddings
    """
    if isinstance(texts, str):
        texts = [texts]

    response = client.embeddings.create(
        model="hkunlp/instructor-large",
        input=texts
    )

    embeddings = [item.embedding for item in response.data]
    return embeddings