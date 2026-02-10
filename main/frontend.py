import streamlit as st
from backend import graph,rename_chat_model
from langgraph.checkpoint.memory import RunnableConfig
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
import uuid,os
from database_utils import create_thread, get_threads,init_schema,update_file_name
from RAG import ingest_pdf

# Set LangSmith Project
os.environ['LANGSMITH_PROJECT'] = "Streamlit Chatbot"

# ********************************************************* Utils ****************************************************
init_schema()

def _gen_thread_id():
    return uuid.uuid4()

def _get_default_user_id():
    return uuid.UUID('00000000-0000-0000-0000-000000000001')

def reset_session():
    st.session_state['thread'] = {"thread_id":_gen_thread_id(),"thread_name":None,"file_name":None}
    st.session_state["message_history"] = []
    st.session_state['thread_file'] = None
    st.rerun() # After reset rerun the state

def serialize_message(message):
    if isinstance(message, AIMessage):
        if message.content:
            return {"role": "assistant", "content": message.content}
    elif isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    elif isinstance(message,ToolMessage):
        return None

    
def load_messages(thread):
    temp = []
    message_history = graph.get_state({"configurable":{"thread_id":thread['thread_id']}}).values['messages']
    for message in message_history:
        serialized  = serialize_message(message) #If ToolMessage returns None 
        if serialized : 
            temp.append(serialized)
    st.session_state["message_history"] = temp


# ********************************************************* Session ****************************************************
if "user_id" not in st.session_state:
    st.session_state['user_id'] = _get_default_user_id()

if "thread" not in st.session_state:
    st.session_state['thread'] = {"thread_id":_gen_thread_id(),"thread_name":None,"file_name":None}

if "thread_list" not in st.session_state:
    st.session_state['thread_list'] = get_threads(user_id= st.session_state['user_id'])

if "message_history" not in st.session_state: # session_state is a dict
    st.session_state["message_history"] = []

# When we click new chat, the uploaded file is ingested again because uploader(session-scoped,) does not reset; To make it thread scoped, Bind the uploader to a thread-specific key and reset it on thread change.
if "thread_file" not in st.session_state:
    st.session_state["thread_file"] = ()


  
# *********************************************************Sidebar****************************************************

st.sidebar.title("Phoenix")

# Handle Reset before loading previous messages
if st.sidebar.button("New Chat", width="stretch"):
    reset_session()

# Load upload button
file = st.sidebar.file_uploader(label="Upload File (allowed one file per chat)",type=[".pdf"],max_upload_size=2,key=f"file_uploader_{st.session_state['thread']['thread_id']}")
if file:
    # Create new file id and get the current thread_id
    new_file_id = (file.name, file.size)
    current_thread_id = st.session_state['thread']['thread_id']
    # Check if the new file is not same as the file uploaded before in the same thread. We can upload the same file accross multiple threads
    if st.session_state["thread_file"] != (current_thread_id,new_file_id):
        file_bytes = file.read()
        ingest_pdf(file_bytes=file_bytes,thread_id=st.session_state['thread']['thread_id'],user_id = st.session_state['user_id'])
        st.session_state["thread_file"] = (current_thread_id,new_file_id)
        st.session_state['thread']['file_name'] = file.name
        update_file_name(file_name=file.name,thread_id=st.session_state['thread']['thread_id'],user_id=st.session_state['user_id'])
        # Get threads from the database and rerun. Always rerun after fetching,resetting,changing threads
        st.session_state['thread_list'] = get_threads(user_id=st.session_state['user_id'])
        st.rerun()

# print(st.session_state['thread'])
if st.session_state['thread']['file_name']:
    st.sidebar.caption(f"Context File : {st.session_state['thread']['file_name']}")

# After messsages load Recent conversations
st.sidebar.caption("Recents")

for thread in (st.session_state['thread_list']):
    if thread['thread_name']:
        if st.sidebar.button(thread['thread_name'],width="stretch",key=f"thread_button_{thread['thread_id']}" ): # Each time you clcik a button whole script runs again
            st.session_state['thread'] = thread.copy() # Create a shallow copy of the dict so session_state gets a new object; # Without .copy(), this would only assign another pointer reference to the same dict.
            st.session_state['thread_file'] = None
            load_messages(st.session_state['thread'])
            st.rerun() # Fixed double click issues; 

# ********************************************************* UI ***********************************************************
# Load previous messages
for message in st.session_state['message_history']:
    with st.chat_message(name=message['role']):
        st.text(message['content'])


# User input
user_input = st.chat_input('Type your query')

# Display welcome message if message_history is empty
if not st.session_state["message_history"]:
    st.markdown(body=
    """
    <div style="text-align:center">

    ## Welcome 👋

    #### What this chatbot can do

    </div>

    **📄 PDF Question Answering**
    - Upload **one PDF per chat**
    - Ask questions grounded strictly in that document
    - To query another PDF, start a **new chat**

    **🎥 YouTube Video Q&A**
    - Provide **one YouTube video per chat**
    - Ask questions based on the video transcript
    - To analyze a different video, start a **new chat**

    **🌦️ Utilities**
    - Weather information
    - Currency conversion
    - Arithmetic and numerical operations

    **🌐 Web Search**
    - Retrieve the latest information from the internet
    - Powered by DuckDuckGo search

    ---
    """,text_alignment="justify",width="stretch",unsafe_allow_html=True)
    
CONFIG : RunnableConfig = {
    "configurable" : {
        "thread_id" : st.session_state['thread']['thread_id'],
        "user_id": st.session_state["user_id"]
    },
    # To configure threads in LangSmith
    "metadata":{"thread_id":st.session_state['thread']['thread_id']},
}

if user_input:
    # Check if it is the first user input, if yes then find thread_name
    if st.session_state['thread']['thread_name'] is None:
        thread_name = rename_chat_model.invoke(f"Create a brief title (3 words max) from the query given only \n{user_input}").content

        # Set thread_name 
        st.session_state['thread']['thread_name'] = thread_name

        # Save to database
        create_thread(thread_id=st.session_state['thread']['thread_id'], thread_name=thread_name,user_id= st.session_state['user_id'])

        # Get fresh list of threads including the current thread
        st.session_state['thread_list'] = get_threads(st.session_state['user_id'])


    # Append user_input to message_history
    st.session_state["message_history"].append({"role":"user","content":user_input})
    
    # Show the latest messages
    with st.chat_message('user'):
        st.text(user_input)
    
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
                        # Chunked AI output
                        elif message_chunk.content != '':
                            # Output will come in tokens therefore store in buffer 
                                ai_message_buffer.append(message_chunk.content)
                                yield message_chunk.content
                    # Tool execution
                    elif isinstance(message_chunk, ToolMessage):
                        status.write(f"Processing `{message_chunk.name}`...")
            # write_stream only expects a generator object
            st.write_stream(unified_stream())

    # concatenate buffer to get the whole AIMessage
    ai_message = "".join(ai_message_buffer)
    # Append ai_message to message_history
    if ai_message:
        st.session_state['message_history'].append({'role':'assistant',"content":ai_message})