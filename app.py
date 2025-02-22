from typing import Callable, TypeVar
import os
import inspect
import streamlit as st
import streamlit_analytics2 as streamlit_analytics
from dotenv import load_dotenv
from streamlit_chat import message
from streamlit_pills import pills
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from streamlit.delta_generator import DeltaGenerator
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from custom_callback_handler import CustomStreamlitCallbackHandler
from agents import define_graph
import shutil

load_dotenv()
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASS")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")    
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
LINKEDIN_JOB_SEARCH = os.getenv("LINKEDIN_JOB_SEARCH")


# Page configuration
st.set_page_config(layout="wide")
st.title("GenAI Career Assistant")

streamlit_analytics.start_tracking()

# Setup directories and paths
temp_dir = "temp"
dummy_resume_path = os.path.abspath("dummy_resume.pdf")

if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Add dummy resume if it does not exist
if not os.path.exists(dummy_resume_path):
    default_resume_path = "resume.pdf"
    shutil.copy(default_resume_path, dummy_resume_path)

# Sidebar - File Upload
uploaded_document = st.sidebar.file_uploader("Upload Your Resume", type="pdf")

if not uploaded_document:
    uploaded_document = open(dummy_resume_path, "rb")
    st.sidebar.write("Using a dummy resume for demonstration purposes. ")
    st.sidebar.markdown(f"[View Dummy Resume]({'https://drive.google.com/file/d/1vTdtIPXEjqGyVgUgCO6HLiG9TSPcJ5eM/view?usp=sharing'})", unsafe_allow_html=True)
    
bytes_data = uploaded_document.read()

filepath = os.path.join(temp_dir, "resume.pdf")
with open(filepath, "wb") as f:
    f.write(bytes_data)

st.markdown("**Resume uploaded successfully!**")
streamlit_analytics.stop_tracking()

settings = {
    "model": "llama-3.1-70b-versatile",
    "model_provider": "groq",
    "temperature": 0.3,
}
# Create the agent flow
flow_graph = define_graph()
message_history = StreamlitChatMessageHistory()

# Initialize session state variables
if "active_option_index" not in st.session_state:
    st.session_state["active_option_index"] = None
if "interaction_history" not in st.session_state:
    st.session_state["interaction_history"] = []
if "response_history" not in st.session_state:
    st.session_state["response_history"] = ["Hello! How can I assist you today?"]
if "user_query_history" not in st.session_state:
    st.session_state["user_query_history"] = ["Hi there! 👋"]

# Containers for the chat interface
conversation_container = st.container()
input_section = st.container()

# Define functions used above
def initialize_callback_handler(main_container: DeltaGenerator):
    V = TypeVar("V")

    def wrap_function(func: Callable[..., V]) -> Callable[..., V]:
        context = get_script_run_ctx()

        def wrapped(*args, **kwargs) -> V:
            add_script_run_ctx(ctx=context)
            return func(*args, **kwargs)

        return wrapped

    streamlit_callback_instance = CustomStreamlitCallbackHandler(
        parent_container=main_container
    )

    for method_name, method in inspect.getmembers(
        streamlit_callback_instance, predicate=inspect.ismethod
    ):
        setattr(streamlit_callback_instance, method_name, wrap_function(method))

    return streamlit_callback_instance

def execute_chat_conversation(user_input, graph):
    callback_handler_instance = initialize_callback_handler(st.container())
    callback_handler = callback_handler_instance
    try:
        output = graph.invoke(
            {
                "messages": list(message_history.messages) + [user_input],
                "user_input": user_input,
                "config": settings,
                "callback": callback_handler,
            },
            {"recursion_limit": 30},
        )
        message_output = output.get("messages")[-1]
        messages_list = output.get("messages")
        message_history.clear()
        message_history.add_messages(messages_list)

    except Exception as exc:
        return ":( Sorry, Some error occurred. Can you please try again?"
    return message_output.content

# Clear Chat functionality
if st.button("Clear Chat"):
    st.session_state["user_query_history"] = []
    st.session_state["response_history"] = []
    message_history.clear()
    st.rerun()  # Refresh the app to reflect the cleared chat

# for tracking the query.
streamlit_analytics.start_tracking()

# Display chat interface
with input_section:
    user_input_query = st.chat_input(
        placeholder="Write your query",
        key="input",
    )
    if user_input_query:
        if not uploaded_document:
            st.error("Please upload your resume before submitting a query.")

        # elif service_provider == "openai" and not st.session_state["OPENAI_API_KEY"]:
        #     st.error("Please enter your OpenAI API key before submitting a query.")

        elif user_input_query:
            # Process the query as usual if resume is uploaded
            chat_output = execute_chat_conversation(user_input_query, flow_graph)
            st.session_state["user_query_history"].append(user_input_query)
            st.session_state["response_history"].append(chat_output)
            st.session_state["last_input"] = user_input_query  # Save the latest input
            st.session_state["active_option_index"] = None

# Display chat history
if st.session_state["response_history"]:
    with conversation_container:
        for i in range(len(st.session_state["response_history"])):
            message(
                st.session_state["user_query_history"][i],
                is_user=True,
                key=str(i) + "_user",
                avatar_style="fun-emoji",
            )
            message(
                st.session_state["response_history"][i],
                key=str(i),
                avatar_style="bottts",
            )

streamlit_analytics.stop_tracking()