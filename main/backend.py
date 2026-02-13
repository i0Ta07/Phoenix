import requests,os,re,asyncio
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Annotated,TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage,AIMessage,ToolMessage,HumanMessage
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.prebuilt import tools_condition
from RAG import get_retriever,create_vector_store
from langchain_core.runnables import RunnableConfig
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_core.documents import Document


from database_utils import get_conn,init_schema
load_dotenv()

# define the state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_call_count:int

# define model
model = ChatOpenAI(model="gpt-5")
rename_chat_model = ChatOpenAI()

# **************************************************** Tools *********************************************************

# Define tools 
search_tool = DuckDuckGoSearchRun()

@tool
def calculator(first_number:float, second_number:float, operation:str) -> dict:
    """
    Perform arithmetic operation between two numbers and returns the result
    Supported operations: add,multiply,divide,subtract
    """
    try:
        if operation == "add":
            result = first_number + second_number
        elif operation == "multiply":
            result = first_number * second_number
        elif operation == "subtract":
            result = first_number - second_number
        elif operation == "divide":
            if second_number == 0:
                return {"error":"Divison by zero not allowed"}
            result = first_number / second_number
        else:
            result = {"error":f"Unsupported operand type:{operation}"}
        return {"result":result}
    except Exception as e:
        return {"error":str(e)}

@tool
def get_weather(latitude:float,longitude:float) -> float:
    """Provide you the temperature in celsius for any given location using it;s latitude and longitude position """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
    response = requests.get(url) # Returns a JSON schema 
    data = response.json()
    return (data['current']['temperature_2m'])

@tool
def get_conversion_rate(base_currency:str,target_currency:str) -> float: # return -> dict:if returning JSON
    """Fetches latest conversion rate between a base currency and target currency"""
    api = os.getenv('EXCHANGE_API_KEY')
    url = f"https://v6.exchangerate-api.com/v6/{api}/pair/{base_currency}/{target_currency}"
    response = requests.get(url) # Returns a JSON object
    data  = response.json() # Converts the JSON into a python dictionary
    return data["conversion_rate"]


# We cannot pass dynmic objects such as retriever in the parameter, we only send static objects such as str,float etc.
@tool
def get_contextPDF(query:str,config:RunnableConfig):
    """
    Retrieve relevant context from the user-uploaded PDF associated with
    the current chat thread.

    Invocation constraint: This tool may be invoked at most once per user query.
    Multiple invocations within the same query are not permitted.
    Thread constraint: In a given chat thread, the first PDF uploaded is treated
    as immutable and defines the single authoritative document for that thread.
    Any subsequent PDFs uploaded in the same thread are ignored, and all retrieval
    is performed exclusively against the originally ingested PDF.

    To query a different PDF, the user must start a new chat/thread.
    
    This tool MUST be used whenever the user's question depends on the
    contents of an uploaded document, including but not limited to:
    - Explicit or implicit references to the document
      (e.g., "my document", "this file", "the uploaded PDF", "the content above")
    - Requests to inspect, analyze, summarize, explain, or evaluate
      information that exists only in the uploaded document
    - Any question where answering without reading the document would
      require assumptions or generalization

    The uploaded document is the authoritative source of truth for all
    document-dependent questions. The model should NOT answer such questions
    using general knowledge or inference without first retrieving context
    via this tool. If no relevant document context is found, explicitly state that the
    answer cannot be determined from the uploaded document.
    """

    user_id = config["configurable"]["user_id"]
    thread_id = config["configurable"]["thread_id"]
    retriever = get_retriever(thread_id, user_id,doc_type="pdf")
    if not retriever:
        return  {"error":"Retriever not initialized. Please upload the PDF to continue"}
    docs = retriever.invoke(query)
    return {
        "context": "\n\n".join(d.page_content for d in docs),
        "metadata": [d.metadata for d in docs]
    }
    
def parseYoutubeURL(url:str)->str:
   data = re.findall(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
   if data:
       return data[0]
   return ""

# Do not return runtime Error objects, return message payload  
@tool
def get_contextYTvideo(query:str,url:str,config:RunnableConfig):
    """
    Retrieve relevant context from a user-provided YouTube video transcript
    associated with the current chat thread.

    Invocation constraint: This tool may be invoked at most once per user query.
    Multiple invocations within the same query are not permitted.

    Thread constraint: In a given chat thread, the first YouTube URL provided
    is treated as immutable and defines the single authoritative video for that
    thread. Any subsequent URLs provided in the same thread are ignored, and all
    retrieval is performed against the transcript of the originally ingested video.

    To query a different YouTube video, the user must start a new chat/thread.

    This tool MUST be used when the user asks a question that depends on the
    contents of a YouTube video, including:
    - Questions referring to the video explicitly or implicitly
      (e.g., "this video", "the YouTube link", "what he says in the video")
    - Requests to summarize, explain, analyze, or extract information
      that exists only in the video content
    - Any query that cannot be answered without reading the video transcript

    The YouTube transcript is the authoritative source of truth for
    video-dependent questions. The model should NOT answer such questions
    from general knowledge or inference without first retrieving context
    using this tool. If no relevant document context is found, explicitly state that the
    answer cannot be determined from the uploaded document
    """
    user_id = config["configurable"]["user_id"]
    thread_id = config["configurable"]["thread_id"]
    retriever = get_retriever(thread_id, user_id,doc_type="YTvideo")
    if not retriever:
        video_id = parseYoutubeURL(url)
        if not video_id:
            return {"error": "Cannot fetch the video link"}
        ytt_api = YouTubeTranscriptApi()
        try:
            transcript_list = ytt_api.fetch(video_id, languages=["en"])
            transcript = ""
            for snippet in transcript_list:
                transcript +=  " " + snippet.text
            docs = [Document(page_content=transcript,metadata={"source": url,"platform": "Youtube"})] # Expects a list of document objects
            create_vector_store(docs=docs,thread_id=thread_id,user_id=user_id,doc_type="YTvideo") 
            retriever = get_retriever(thread_id, user_id,doc_type="YTvideo")
        except TranscriptsDisabled:
            return ("No captions available for the video")
        except Exception as e:
            return {"error":f"Failed to create video vector store; Error: {str(e)}"}
    docs = retriever.invoke(query)
    return {
        "context": "\n\n".join(d.page_content for d in docs),
        "metadata": [d.metadata for d in docs]
    }
    
tools = [search_tool,calculator,get_conversion_rate,get_weather,get_contextPDF,get_contextYTvideo]
tool_llm = model.bind_tools(tools)


# ******************************************************** Graph Fucntions ********************************************

MAX_TOOL_CALLS = 5
tool_map = {}
for tool in tools:
    tool_map[tool.name] = tool

# define fucntion
def chat(state:ChatState):
    messages = state['messages']
    response = tool_llm.invoke(messages) # Invoke using tool node
    if isinstance(messages[-1], HumanMessage):
        return {
            'messages': [response],
            'tool_call_count': 0
        }
    
    return {'messages': [response]} # Return as list for later concatenation with existing message list.


def tool(state:ChatState):
    last_message = state['messages'][-1]
    current_count = state.get("tool_call_count",0)

    if isinstance(last_message,AIMessage) and last_message.tool_calls:
        response = []
        for tc in last_message.tool_calls:
            if current_count < MAX_TOOL_CALLS:
                result = tool_map[tc["name"]].invoke(tc["args"])
                current_count += 1
            else:
                result  = result = f"Tool call limit exceeded: Only {MAX_TOOL_CALLS} tool calls are allowed per query. You have already made {current_count} calls. Please provide a final answer with the information gathered so far."
            tool_message = ToolMessage(content = str(result),tool_call_id = tc["id"],name = tc["name"])
            response.append(tool_message)
        return {'messages': response, 'tool_call_count':current_count}
    
# Have to convert postgres, all other node(ainvoke) and stream(astream) to implement Async. One async all async

async def async_tool(state:ChatState):
    last_message = state['messages'][-1]
    current_count = state.get("tool_call_count",0)

    tool_calls = last_message.tool_calls

    remaining_quota = max(0,MAX_TOOL_CALLS - current_count)
    allowed_calls = tool_calls[:remaining_quota] # from zero to remaining_quota - 1
    denied_calls = tool_calls[len(allowed_calls):] # from len(allowed) till last

    response = []

    async def run_tool(tc):
        tool_name = tc["name"]
        try:
            result = await tool_map[tool_name].ainvoke(tc['args']) # returns a coroutine that must be awaited before converting to string
        except Exception as e:
            result = f"Tool execution error: {str(e)}"
        return tc, result
    
    tasks = [run_tool(tc) for tc in allowed_calls] # Create coroutines(tasks that will run together) in a list

    if tasks:
        # Send coroutines for parallel execution
        completed = await asyncio.gather(*tasks) # Need coroutines as arguments not a list, therefore unpack
        for tc, result in completed:
            response.append(ToolMessage(content=str(result),tool_call_id = tc['id'],name = tc['name']))

    for tc in denied_calls:
        response.append(ToolMessage(content=f"Tool call limit exceeded: Only {MAX_TOOL_CALLS} tool calls are allowed per query. You have already made {current_count + len(allowed_calls)} calls. Please provide a final answer with the information gathered so far.",
            tool_call_id = tc['id'],name = tc['name']))

    return{
        "messages":response,
        "tool_call_count": current_count + len(allowed_calls)
    }

# Create Graph
builder = StateGraph(ChatState)


# Define nodes and edges
builder.add_node("chat_node",chat)
builder.add_node("tools",tool)

builder.add_edge(START,"chat_node")
builder.add_conditional_edges("chat_node",tools_condition)
builder.add_edge("tools","chat_node") # Connect tool_node to process node again

init_schema()

# Create a postgres connection object
conn = get_conn()

# Create checkpointer
checkpointer = PostgresSaver(conn)

checkpointer.setup()

# Compile the graph
graph = builder.compile(checkpointer=checkpointer)


