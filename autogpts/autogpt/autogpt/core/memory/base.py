import os
from typing import List, Any
import abc
import openai

from autogpt.core.prompting.schema import ChatMessage
from autogpt.llm.utils import create_openai_chat_completion, create_openai_embedding

class Memory(abc.ABC):
    pass


class MemoryItem(abc.ABC):
    pass


class MessageHistory(abc.ABC):
    pass

# -------------------------------------------------

class AgentMemoryItem(MemoryItem):
    
    def __init__(self, role, message) -> None:
        super().__init__()

        self.role: str = role
        self.message: str = message
    
    def format(self) -> str:
        
        return f"{self.role}: {self.message}\n"

class AgentMessageHistory(MessageHistory):
    
    def __init__(self) -> None:
        super().__init__()

        self.history: List[AgentMemoryItem] = []
    
    def append(self, item: AgentMemoryItem) -> None:
        
        self.history.append(item)
    
    @property
    def size(self) -> int:
        
        return len(self.history)
    
    def format(self) -> str:
        
        message_str = ""       
        for _, item in enumerate(self.history):
            message_str += item.format()
        
        return message_str

class AgentMemory(Memory):
    
    def __init__(self) -> None:
        super().__init__()
        
        self.messages: AgentMessageHistory = AgentMessageHistory()
        self.fetched_memory: List[str] = []
    
    def append_message(self, role, message):
        
        self.messages.append(AgentMemoryItem(role, message))
    
    def format(self) -> str:
        
        memory_template = (
        "## Chat Messages:\n"
        "{messages}\n"
        )

        return memory_template.format(
            messages=self.messages.format()
        )
    
    def summarize(self) -> dict:
        
        prompt = "Please summarize the following chat between user and ai system:\n"
        prompt += self.messages.format()

        memory_summary = create_openai_chat_completion(
            messages=[ChatMessage.system(prompt)])
        vec = create_openai_embedding(
            input=[memory_summary])[0]

        # response = openai.ChatCompletion.create(
        #     model="gpt-3.5-turbo-0125",
        #     api_key=os.getenv("OPENAI_API_KEY"),
        #     messages=[
        #         {"role": "system", 
        #          "content": prompt},
        #     ]
        # )
        # memory_summary = response.choices[0].message.content
        # vec = openai.Embedding.create(
        #     model="text-embedding-3-small",
        #     api_key=os.environ.get("OPENAI_API_KEY"),
        #     input=memory_summary).data[0].embedding
        

        return {
            "Content": memory_summary,
            "Embedding": vec
        }
    
    def fmt_fetched_memory(self) -> ChatMessage:
        
        if self.fetched_memory:
            prompt = "Previous memory between system and user ordered by relatedness:\n"
            for i, m in enumerate(self.fetched_memory):
                prompt += f"  {i}. "
                for k, v in m.items():
                    prompt += f"{k}:{v} "
                prompt += "\n"
        
        return ChatMessage.system(prompt)