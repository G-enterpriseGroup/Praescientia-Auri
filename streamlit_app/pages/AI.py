import streamlit as st
import openai

st.title("O1 Chatbot")

# Set your API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

def get_bot_response(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",  # or your preferred model/engine
        prompt=prompt,
        max_tokens=150,
        temperature=0.7,
        n=1,
        stop=None,
    )
    return response.choices[0].text.strip()

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Input box for user text
user_input = st.text_input("You:")

if st.button("Send") and user_input:
    # Append user message
    st.session_state.chat_history.append(("User", user_input))
    # Get and append bot response
    bot_response = get_bot_response(user_input)
    st.session_state.chat_history.append(("Bot", bot_response))

# Display conversation
for speaker, message in st.session_state.chat_history:
    st.markdown(f"**{speaker}:** {message}")
