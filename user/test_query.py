import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA, ConversationalRetrievalChain
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec


# Setup environment variables
os.environ["OPENAI_API_KEY"] = ""
os.environ["PINECONE_API_KEY"] = ""

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINECONE_API_KEY = os.environ['PINECONE_API_KEY']

print('os', os.getcwd())

# Load documents and split them into chunks
loader = DirectoryLoader('./user/static', glob="./*.pdf", loader_cls=PyPDFLoader)
documents = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

# Initialize Pinecone and create an index
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = 'ai4edu-test'

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric='euclidean',
        spec=ServerlessSpec(cloud='aws', region="us-east-1")
    )

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
docsearch = PineconeVectorStore.from_documents(texts, embeddings, index_name=index_name)

# Initialize the Conversational Retrieval Chain
llm = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY, model_name="gpt-4-turbo", streaming=True)
retriever = docsearch.as_retriever(include_metadata=True, metadata_key='source')

qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

chat_history = []

# FastAPI router
router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list

def parse_response(response):
    sources = []
    for source_name in response["source_documents"]:
        source_info = source_name.metadata.get('source', 'Unknown source')
        page_info = source_name.metadata.get('page', 'Unknown page')
        sources.append(f"{source_info} page #: {page_info}")
    return response['answer'], sources

@router.post("/test_query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    global chat_history
    try:
        response = qa_chain({"question": request.question, "chat_history": chat_history})
        answer, sources = parse_response(response)
        chat_history.append((request.question, response['answer']))
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test_query/history")
async def get_history():
    return {"chat_history": chat_history}

@router.get("/test_query/clear_history")
async def get_history():
    global chat_history
    chat_history = []
    return {"chat_history": chat_history}

