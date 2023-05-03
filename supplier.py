import openai
import json
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

sys_msg = [{
    "role": "system",
    "content": "Hi, I'm a chatbot! Ask me a question."
}]
initial_msg = []

def send_chat(text,messages=initial_msg):
    '''
    send_chat function takes two arguments: text and messages

    text: the text that the user inputs
    messages: a list of tuples, each tuple contains two strings, the first string is the user input, the second string is the assistant output

    return: a tuple, the first element is an empty string, the second element is the updated messages list

    '''
    openai_messages = sys_msg.copy()

    for m in messages:
        openai_messages.extend([
            {
                "role": "user",
                "content": m[0]
            },
            {
                "role": "assistant",
                "content": m[1]
            }
        ])

    openai_messages.extend([
        {
            "role": "user",
            "content": text
        }
    ])

    res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=openai_messages
        )
    
    assistant_text = res.choices[0]["message"]["content"]
    
    messages.append((text,assistant_text))

    return "",messages
