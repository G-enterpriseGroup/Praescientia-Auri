import streamlit as st
import openai

# Ensure you replace 'your_openai_api_key' with the actual API key.
# Consider using environment variables for better security.
api_key = "sk-proj-vS65oAiqtzRkhFlMxUBbT3BlbkFJHY4gBJITcNn7NbYKaBDX"

def get_response(message, api_key):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message}],
        api_key=api_key
    )
    return response['choices'][0]['message']['content']

st.title('ChatGPT Chat Interface')
user_input = st.text_input("Type your message:")

if user_input:
    response = get_response(user_input, api_key)  # Pass the API key here
    st.text_area("ChatGPT Response:", value=response, height=200)
