from openai import OpenAI
import streamlit as st
import time

st.title("ChatGPT-like clone")

# Initialize the OpenAI client
try:
    client = OpenAI(api_key="sk-balraj-KLoW4HxnPDr6efjrLIFlT3BlbkFJFey4fhZcJMWgg1zIqmyB")
except Exception as e:
    st.error(f"Failed to authenticate with OpenAI: {e}")
    st.stop()

# Session state for model and messages
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input from the user
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        # Check rate limit before making a request
        if 'last_request_time' in st.session_state:
            elapsed_time = time.time() - st.session_state.last_request_time
            if elapsed_time < 1:  # simple rate limiter, adjust as necessary
                st.warning("You're sending messages too quickly. Please wait a moment.")
                st.stop()
        
        # Request to OpenAI
        response = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        ).choices[0].message["content"]
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.last_request_time = time.time()
    except Exception as e:
        st.error(f"Failed to generate response from OpenAI: {e}")
