import streamlit as st
import openai

st.title("O1 Chatbot")

# Set your API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_bot_response(prompt):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    # Using the new ChatCompletion API endpoint
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # or your chosen model
        messages=messages,
        temperature=0.7,
    )
    return response["choices"][0]["message"]["content"].strip()

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

user_input = st.text_input("You:")

if st.button("Send") and user_input:
    # Append user message
    st.session_state.chat_history.append(("User", user_input))
    # Get and append bot response
    bot_response = get_bot_response(user_input)
    st.session_state.chat_history.append(("Bot", bot_response))

# Display the conversation
for speaker, message in st.session_state.chat_history:
    st.markdown(f"**{speaker}:** {message}")
