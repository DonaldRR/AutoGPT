import os
from typing import Any
import logging

# Supabase
import supabase
from supabase import create_client, Client
# Langchain
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
# autogpt 
from autogpt.agents.agent import AgentSettings
from autogpt.config.ai_profile import AIProfile
from autogpt.config.ai_directives import AIDirectives
from autogpt.logs import color_logger
# forge
from forge.sdk.db import AgentDB

logger = logging.getLogger(__name__)
color_logger(logger)

from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)
del load_dotenv

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
            logger.info("💾 Supabase connected")
        else:
            logger.warning("💾 Cannot connect to Supabase")   
    
    def sign_in(self, user_name: str, password: str) -> bool:
        
        try:
            res = self.client.auth.sign_in_with_password({
                "email": user_name,
                "password": password
            })
            self.user_id = res.user.id
            # logger.info(f"Database sign in: {res}")
        except Exception as e:
            logger.warning(f"Sign in Error: {e}")
            return False

        return True

    def update_agent(self, settings: AgentSettings) -> bool:

        table_name = "AgentSetting"
        try:
            ai_profile: AIProfile = settings.ai_profile
            ai_directives: AIDirectives = settings.directives

            data = {
                "UserId": self.user_id,
                # "Name": ai_profile.ai_name,
                # "Description": ai_profile.ai_role,
                # "BestPractices": "\n".join(ai_directives.best_practices),
                # "Constraints": "\n".join(ai_directives.constraints),
                # "Resources": "\n".join(ai_directives.resources)
                "Setting": settings.json()
            }

            res = self.client.table(table_name).upsert(data).execute()
        except Exception as e:
            logger.info(f"Update {table_name} Table Error:{e}")
            return False
        
        return True
    
    def get_agent(self, settings: AgentSettings) -> AgentSettings:
        
        table_name = "AgentSetting"

        try: 
            res = self.client.table(table_name)\
                .select('*').eq('UserId', self.user_id).execute().data
            if len(res) > 0:
                res = res[0]
                # value handle 
                str_mapping = {
                    "null": "None",
                    "false": "False",
                    "true": "True",
                }
                for k, v in str_mapping.items():
                    res["Setting"] = res["Setting"].replace(k, v)
                settings = AgentSettings.parse_obj(eval(res["Setting"]))

        except Exception as e:
            logger.warning(f"Get agent settings Error: {e}")
        
        return settings 
    
    def upsert(self, table_name: str, data: dict):
        
        res = None
        try:
            if table_name:
                res = self.client.table(table_name).upsert(data).execute()
            else:
                res = self.client.table(self.table_name).upsert(data).execute()
        except Exception as e:
            logger.error(e)

        return res
    
    def fetch(self, table_name: str, data: dict):

        if table_name:
            req = self.client.table(table_name).select('*')
        else:
            req = self.client.table(self.table_name).select('*')
        for k, v in data.items():
            req = req.eq(k, v)

        res_data = []
        try:
            res = req.execute()
            res_data = res.data
        except Exception as e:
            logger.error(e)
        
        return res_data
    
    def rpc(self, procedure_name: str, params: dict) -> Any:
        
        print("!!!!!!!!!!!! rpc params", params.keys())
        query_builder = self.client.rpc(procedure_name, params)
        # query_builder.params = query_builder.params.set("limit", 5)
        res = query_builder.execute()        

        return res


def configure_db(db_type: str) -> AgentDB | SupaDB | None:
    
    if db_type == "AgentDB":
        DATABASE_SERVER_URL = os.getenv("AP_SERVER_DB_URL", "sqlite:///data/ap_server.db")
        print(f"DATABASE SERVER URL: {DATABASE_SERVER_URL}")
        # Set up & start server
        database = AgentDB(
            database_string=DATABASE_SERVER_URL,
            debug_enabled=False,
        )
        return database
    elif db_type == "SupaDB":
        database = SupaDB()
        return database
    
    return None

if __name__ == "__main__":

    db = configure_db("SupaDB")

    db.sign_in(user_name="root@chat.com", password="123456")
    data = {"UserId": db.user_id}
    import pdb; pdb.set_trace()