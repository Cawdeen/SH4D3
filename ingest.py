import os
from llama_index.llms import OpenAI
from dotenv import load_dotenv
load_dotenv()

#for embedded RAG query
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
from llama_index import SimpleDirectoryReader, VectorStoreIndex

def ingest():
    # load documents
    documents = SimpleDirectoryReader("data").load_data()

    # build index
    index = VectorStoreIndex.from_documents(
        documents,
        show_progress=True
    )
    # Store the index
    index.storage_context.persist(persist_dir="index")