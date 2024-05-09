import streamlit as st
import openai

def get_response(message):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message}],
        api_key="your_openai_api_key"
    )
    return response['choices'][0]['message']['content']

st.title('ChatGPT Chat Interface')
user_input = st.text_input("Type your message:")

if user_input:
    response = get_response(user_input)
    st.text_area("ChatGPT Response:", value=response, height=200)
