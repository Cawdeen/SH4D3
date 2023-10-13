
import openai
import os
from dotenv import load_dotenv
from llama_index.llms import OpenAI
from llama_index import ServiceContext, set_global_service_context
from llama_index import StorageContext, load_index_from_storage
from llama_index.llms import OpenAI
load_dotenv()

class Querybot:

    def __init__(self):
        OpenAI.api_key = os.getenv("OPENAI_API_KEY")
        #basic who are you prompt
        self.startingprompt = "You are a droid named SH4D3 in a Star Wars video game. You're in Mos Pelgo, Tatooine. Be a little sarcastic, keep responses brief. Use emoji sparingly. Include some static and stuttering in your responses since you're a droid. "
        ############################# openai
        #for openai API
        #openai.api_key = os.getenv("OPENAI_API_KEY")
        #openai.Model.list()
        
        self.chat_countdown = 0 #countdown timer to reset chat in minutes
        self.chat_countdown_max = 45
        # define LLM
        self.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.6, max_tokens=900)

        # configure service context
        self.service_context = ServiceContext.from_defaults(llm=self.llm, chunk_size=900, chunk_overlap=20)
        set_global_service_context(self.service_context)
        self.load_context()
        #configure index
        self.storage_context = StorageContext.from_defaults(persist_dir="index")#load index
        self.index = load_index_from_storage(self.storage_context)
        self.query_engine = self.index.as_query_engine(similarity_top_k=2)#build query engine
        self.chat_engine = self.index.as_chat_engine(chat_mode='context', similarity_top_k=2)#build chat engine

    def load_context(self):
        self.storage_context = StorageContext.from_defaults(persist_dir="index")#load index
        self.index = load_index_from_storage(self.storage_context)
        self.query_engine = self.index.as_query_engine(similarity_top_k=2)#build query engine
        self.chat_engine = self.index.as_chat_engine(chat_mode='context', similarity_top_k=2)#build chat engine
        print('Finished loading context')

    def handle_chat_request(self, prompt):
        chat_exists = self.chat_in_progress() #is there already a chat
        response = ''
        if chat_exists == False: #new chat
            print('New prompt constructed')
            prompt = self.startingprompt + prompt #add the starting prompt for context     
        response = self.chat(prompt)
        return response

    def countdown(self):
        if self.chat_countdown > 1:
            self.chat_countdown -= 1
        elif self.chat_countdown == 1:
            self.chat_countdown = 0
            self.chat_engine.reset()
            print('chat is now reset')
    
    #returns true if there is a current chat in progress, otherwise returns false
    def chat_in_progress(self):
        if self.chat_countdown >= 1:
            print('Returning chat in progress')
            return True
        else:
            print('Returning chat not in progress')
            return False
    
    def chat(self, prompt):
        response = self.chat_engine.chat(prompt)
        self.chat_countdown = self.chat_countdown_max
        return response


