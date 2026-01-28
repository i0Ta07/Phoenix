import sqlite3,requests,os
from langgraph.graph import StateGraph, START,END
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Annotated,TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.prebuilt import ToolNode,tools_condition

load_dotenv()

# define the state
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# define model
model = ChatOpenAI(model="gpt-4o")
rename_chat_model = ChatOpenAI()

# **************************************************** Tools *********************************************************

# Define tools 
search_tool = DuckDuckGoSearchRun()

@tool
def calculator(first_number:float, second_number:float, operation:str) -> dict:
    """
    Perform arithmetic operation between two numbers and returns the result
    Supported operations: add,mutiply,divide,subtract
    """
    try:
        if operation == "add":
            result = first_number + second_number
        elif operation == "muliply":
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

# Create Tool
@tool
def get_conversion_rate(base_currency:str,target_currency:str) -> float: # return -> dict:if returning JSON
    """Fetches latest conversion rate between a base currency and target currency"""
    api = os.getenv('EXCHANGE_API_KEY')
    url = f"https://v6.exchangerate-api.com/v6/{api}/pair/{base_currency}/{target_currency}"
    response = requests.get(url) # Returns a JSON object
    data  = response.json() # Converts the JSON into a python dictionary
    return data["conversion_rate"]


tools = [search_tool,get_conversion_rate,get_weather]
tool_llm = model.bind_tools(tools)


# ******************************************************** Graph Fucntions ********************************************

# define fucntion
def chat(state:ChatState):
    messages = state['messages']
    response = tool_llm.invoke(messages) # Invoke using tool node
    return {'messages':[response]} # Return as list for later concatenation with existing message list.

# Create Graph
builder = StateGraph(ChatState)

# Create tool_node using pre-built ToolNode, provide it tools
tool_node = ToolNode(tools)

# Define nodes and edges
builder.add_node("chat_node",chat)
builder.add_node("tools",tool_node)

builder.add_edge(START,"chat_node")
builder.add_conditional_edges("chat_node",tools_condition)
builder.add_edge("tools","chat_node") # Connect tool_node to process node again

# Create a sqlite3 connection object
conn = sqlite3.connect(database="threads.db",check_same_thread=False)

# Create checkpointer
checkpointer = SqliteSaver(conn)

# Compile the graph
graph = builder.compile(checkpointer=checkpointer)


