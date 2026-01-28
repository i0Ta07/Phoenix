import streamlit as st
from backend import graph,rename_chat_model
from langgraph.checkpoint.memory import RunnableConfig
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
import uuid,os
from database_utils import create_thread,get_threads

# Set LangSmith Project
os.environ['LANGSMITH_PROJECT'] = "Streamlit Chatbot"

# ********************************************************* Utils ****************************************************

def gen_thread_id():
    return uuid.uuid4()

def reset_session():
    st.session_state['thread'] = {"thread_id":gen_thread_id(),"name":None}
    st.session_state["message_history"] = []

def serialize_message(message):
    if isinstance(message, AIMessage):
        if message.content:
            return {"role": "assistant", "content": message.content}
    elif isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    else:
        return None # If ToolMessage return None

    
def load_messages(thread_id):
    st.session_state['thread']['thread_id'] = thread_id
    st.session_state["message_history"] = []
    message_history = graph.get_state({"configurable":{"thread_id":thread_id}}).values['messages']
    for message in message_history:
        serialized  = serialize_message(message) #If ToolMessage returns None 
        if serialized : 
            st.session_state["message_history"].append(serialized )

# Rebuild state from the database; never incrementally patch session state.
def update_threads():
    threads_list = []
    for thread_id, chat_name in get_threads():
        threads_list.append({"thread_id":uuid.UUID(thread_id),"name":chat_name})
    return threads_list 


# ********************************************************* Session ****************************************************

if "message_history" not in st.session_state: # session_state is a dict
    st.session_state["message_history"] = []

if "thread_list" not in st.session_state:
    st.session_state['thread_list'] = update_threads()

if "thread" not in st.session_state:
    st.session_state['thread'] = {"thread_id":gen_thread_id(),"name":None}


# *********************************************************Sidebar****************************************************

st.sidebar.title("Phoenix")

# Handle Reset before loading previous messages
if st.sidebar.button("New Chat", width="stretch"):
    reset_session()

# After messsages load Recent conversations
st.sidebar.caption("Recents")

for thread in reversed(st.session_state['thread_list']):
    if thread['name']:
        if st.sidebar.button(thread['name'],width="stretch"): # Each time you clcik a button whole script runs again
            load_messages(thread['thread_id'])

# ********************************************************* UI ***********************************************************
# Load previous messages
for message in st.session_state['message_history']:
    with st.chat_message(name=message['role']):
        st.text(message['content'])


# User input
user_input = st.chat_input('Type your query')

# Display welcome message if message_history is empty and there is no user_input
if  (len(st.session_state["message_history"]) == 0) and not user_input:
    st.title(body="Welcome",text_alignment="center")

CONFIG : RunnableConfig = {
    "configurable" : {"thread_id" : st.session_state['thread']['thread_id']},
    # To configure threads in LangSmith
    "metadata":{"thread_id":st.session_state['thread']['thread_id']},
}

if user_input:
    # Check if it is the first user input, if yes then find chat_name
    if len(st.session_state['message_history']) == 0:
        chat_name = rename_chat_model.invoke(f"Create a brief title (3 words max) from the query given only \n{user_input}").content

        # Set name to state and append the thread to the list
        st.session_state['thread']['name'] = chat_name
        
        # Create a snapshot(shallow copy) and save it to the in the list.
        st.session_state['thread_list'].append((st.session_state['thread']).copy())

        # Save to database
        create_thread(thread_id=f"{st.session_state['thread']['thread_id']}",chat_name=chat_name)

    # Show the latest messages
    with st.chat_message('user'):
        st.text(user_input)
    
    # Append user_input to message_history
    if user_input:
        st.session_state["message_history"].append({"role":"user","content":user_input})

    stream = graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode="messages",
    )

    ai_message_buffer = []
    with st.status("Processing...", expanded=True) as status:
        with st.chat_message("assistant"):
            def unified_stream():
                for message_chunk, metadata in stream:
                    if isinstance(message_chunk, AIMessage) :
                        # Tool planning
                        if  len(message_chunk.tool_calls) > 0:
                            for tool_call in message_chunk.tool_calls:
                                if tool_call['name']:
                                    status.write(f"Calling `{tool_call['name']}`...")
                        # Final AI output
                        elif message_chunk.content != '':
                            # Output will come in tokens therefore store in buffer and convert string from buffer
                                ai_message_buffer.append(message_chunk.content)
                                yield message_chunk.content
                    # Tool execution
                    elif isinstance(message_chunk, ToolMessage):
                        status.write(f"Processing `{message_chunk.name}`...")
            # write_stream only expects a generator object
            st.write_stream(unified_stream())


    ai_message = "".join(ai_message_buffer)
    # Apeend ai_message to message_history
    if ai_message:
        st.session_state['message_history'].append({'role':'assistant',"content":ai_message})