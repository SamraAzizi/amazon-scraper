from langchain_openai import OpenAIEmbeddings
import os


def get_embeddings():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY must be set")
    return OpenAIEmbeddings(model="text-embedding-3-small")