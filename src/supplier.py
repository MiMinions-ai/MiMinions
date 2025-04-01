import openai
import boto3
import os

import pydub
import numpy as np

# setup the api keys
openai.api_key = os.environ.get("OPENAI_API_KEY")
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

sys_msg = [{
    "role": "system",
    "content": "Hi, I'm a chatbot! Ask me a question."
}]

App_state = {
    "messages":[],
    "sys_msg":[{
    "role": "system",
    "content": "Hi, I'm a chatbot! Ask me a question."
}],
    "language":"en",
    # "last_msg":"",
    "voice":"Joanna",
}

# setup the polly client
polly_client = boto3.client(
    "polly", # the service we want to use
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name='us-east-1')

def get_voices():
    return polly_client.describe_voices()["Voices"]

# return the audio based on the text
def text_to_audio(messages,voice="Joanna",sample_rate = 22050):
    text = messages[-1][1]
    response = polly_client.synthesize_speech(VoiceId=voice,
                OutputFormat='mp3',
                SampleRate=str(sample_rate),
                Text = text)
    
    buffer = response["AudioStream"].read()
    audio_stream = np.frombuffer(buffer,dtype=np.uint16)
    

    return sample_rate,audio_stream

def send_chat(text,messages=[]):
    '''
    send_chat function takes two arguments: text and messages

    text: the text that the user inputs
    messages: a list of tuples, each tuple contains two strings, the first string is the user input, the second string is the assistant output

    return: a tuple, the first element is an empty string, the second element is the updated messages list

    '''
    openai_messages = App_state["sys_msg"]

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
    App_state.update({"messages":messages})

    return "",messages

def translate(file_path):
    if file_path:
        f = open(file_path,"rb")
        res = openai.Audio.translate("whisper-1",f)
        return res["text"]
    else:
        return ""