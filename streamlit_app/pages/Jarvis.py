from openai import OpenAI
import streamlit as st
import time

st.title("ChatGPT-like clone")

# Initialize the OpenAI client with error handling for API key issues
try:
    client = OpenAI(api_key="your_api_key_here")  # Replace with your actual API key
except Exception as e:
    st.error(f"Failed to authenticate with OpenAI: {e}")
    st.stop()

# Setup session state for model selection and message tracking
if "openai_model" not in st.session_state:
    # Update with an available model for free tier users, e.g., 'gpt-3.5-turbo-0301'
    st.session_state["openai_model"] = "gpt-3.5-turbo-0301"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        # Implementing a simple rate limiter
        if 'last_request_time' in st.session_state:
            elapsed_time = time.time() - st.session_state.last_request_time
            if elapsed_time < 5:  # Adjusted to 5 seconds for safer rate limiting
                st.warning("Please wait a bit before sending another message.")
                st.stop()

        # Call to OpenAI's API with proper error handling
        response = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        ).choices[0].message["content"]

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.last_request_time = time.time()  # Update the time of the last request
    except Exception as e:
        st.error(f"Failed to generate response from OpenAI: {e}")
