import os
import logging
# dev
from .forge_log import ForgeLogger
# Supabase
import supabase
from supabase import create_client, Client
# Langchain
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore

LOG = ForgeLogger(__name__)

class SupaDB:

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_api = os.environ.get("SUPABASE_SERVICE_KEY")

    def __init__(self):

        self.client: supabase.client.Client = None
        self.user_id: str = None
        self.vectorstore: SupabaseVectorStore = None
        self.embedding = OpenAIEmbeddings(
            openai_api_key=os.environ.get("OPENAI_KEY"))

        self._init = False
        self._connect()
    
    def _connect(self):
        
        self.client = create_client(
            SupaDB.supabase_url, 
            SupaDB.supabase_api)
        if self.client:
            self._init = True
            LOG.info("💾 Supabase connected")
        else:
            LOG.warning("💾 Cannot connect to Supabase")   

    async def create_profile(self):
        
        pass

    async def upsert_knowledge(self):
        
        pass

    async def create_step(self):
        
        pass

    async def get_step(self):
        
        pass

    async def update_step(self):
        
        pass

    async def list_steps(self):
        
        pass