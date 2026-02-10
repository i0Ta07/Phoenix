import tempfile,uuid,os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from typing import Dict, Tuple,Literal

load_dotenv()
EMBEDDING_MODEL = OpenAIEmbeddings(model="text-embedding-3-small")
BASE_DIR =  Path.cwd()

RetrieverCacheKey = Tuple[uuid.UUID, uuid.UUID,Literal["YTvideo", "pdf"]]

_RETRIEVER_CACHE: Dict[RetrieverCacheKey, any] = {}

def create_vector_store(docs,thread_id:uuid.UUID,user_id:uuid.UUID,doc_type: Literal["YTvideo", "pdf"]):
    try:
        # Perform Chunking
        recursuive_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 900,
            chunk_overlap = 150,
            separators=["\n\n", "\n", " ", ""]
        )

        chunks = recursuive_splitter.split_documents(docs)

        # Create Embediings
        vector_store = FAISS.from_documents(
            documents=chunks,
            embedding=EMBEDDING_MODEL
        )

        # Save inside current directory
        path = BASE_DIR / "data" / "faiss_store" / doc_type / str(user_id) / str(thread_id)

        # Create path if not exists
        path.mkdir(parents=True, exist_ok=True)

        vector_store.save_local(
            folder_path=str(path),
            index_name=str(thread_id)
        )
    except Exception as e:
        raise RuntimeError(f"Could not create vector store; Error: {e}") from e


def ingest_pdf(file_bytes,thread_id:uuid.UUID,user_id:uuid.UUID):
    temp_path = None
    try:
        # Creates a temp file with some path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="rag") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

            # Create Loader
            pdf_loader = PyPDFLoader(temp_file.name) # Need path, therfore create temp path
            docs = pdf_loader.load()

            create_vector_store(docs,thread_id,user_id,doc_type="pdf")

    except Exception as e:
        raise RuntimeError(f"Could not ingest pdf; Error: {e}") from e
    
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def get_retriever(thread_id:uuid.UUID,user_id:uuid.UUID, doc_type: Literal["YTvideo", "pdf"]):
    key = (user_id, thread_id,doc_type)

    # Fast path: cache hit
    if key in _RETRIEVER_CACHE:
        return _RETRIEVER_CACHE[key]
    
    # Slow path: load from disk
    path  = BASE_DIR / "data" / "faiss_store" / doc_type / str(user_id) / str(thread_id)
    if Path(path).exists():
        vector_store = FAISS.load_local(str(path), EMBEDDING_MODEL, allow_dangerous_deserialization=True,index_name=str(thread_id))
        retriever = vector_store.as_retriever(search_type='similarity',search_kwargs={"k":5})
        _RETRIEVER_CACHE[key] = retriever
        return retriever
    return None

    
