import os
from typing import List
import openai

from autogpt.core.prompting.schema import ChatMessage

def create_openai_chat_completion(messages: List[ChatMessage], model="gpt-3.5-turbo-0125") -> str:
    
    response = openai.ChatCompletion.create(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        messages=[
            {"role": message.role, "content": message.content}
            for message in messages
        ]
    )

    return response.choices[0].message.content

def create_openai_embedding(input: List[str], model="text-embedding-3-small") -> List[List[float]]:
    
    vecs = openai.Embedding.create(
        model=model,
        api_key=os.environ.get("OPENAI_API_KEY"),
        input=input).data
    vecs = [vec.embedding for vec in vecs]

    return vecs