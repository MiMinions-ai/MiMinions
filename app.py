import gradio as gr
from supplier import *

background_examples=[
    "This is a friendly chatbot with humour.", # casual setting
    "This is a friendly chatbot which respond to user in Chinese.", # romantic setting
    "We are at the mideval castle, I am talking to my chatbot donkey.", # fantasy setting
]

# create a system setting for llm
with gr.Blocks() as settings:
    with gr.Row():
        background = gr.TextArea(App_state["sys_msg"][0]["content"],lines=5,label="Current background")
        with gr.Column():
            def update_sys(text):
                App_state["sys_msg"][0].update({"content":text})
                return text
            
            background_edit = gr.Textbox(placeholder="change the background here",label="update background",lines = 5)
            background_edit.submit(update_sys,background_edit,background)
            with gr.Row():
                clear = gr.Button("Clear")
                submit = gr.Button("Submit")

            gr.Examples(background_examples,background_edit,label="Examples")
            clear.click(lambda:None,None,background_edit,queue=False)
            submit.click(update_sys,background_edit,background,queue=False)
    with gr.Row():
        voices_list = gr.Dropdown([v["Name"] for v in get_voices()],label="Voices")
        
    voices_list.change(lambda voice:App_state.update({"voice":voice}),voices_list,queue=False)
            
with gr.Blocks() as chat_window:
    with gr.Row():
        with gr.Column():
            chatbot = gr.Chatbot([])
            chatbot_speech = gr.Audio()
            with gr.Column():
                chat_clear = gr.Button("Clear")
                play_speech = gr.Button("Play")
        chat_clear.click(lambda:None,None,chatbot,queue=False)
        play_speech.click(text_to_audio,chatbot,chatbot_speech,queue=False)

        with gr.Column():
            msg = gr.Textbox()
            submit = gr.Button("Submit")
            gr.Examples(["Hello","How are you?"],msg,label="Examples")
            audio = gr.Audio(source="microphone",type="filepath")
            # gr.Interface(translate,inputs=gr.Audio(source="microphone",type="filepath"),outputs = "text")

        audio.change(translate,audio,msg,queue=False)
        msg.submit(send_chat,[msg,chatbot],[msg,chatbot])
        submit.click(send_chat,[msg,chatbot],[msg,chatbot],queue=False)



iface = gr.TabbedInterface(
    [chat_window,settings],
    ["Chat","Settings"],
    title="MiMinions.ai",
    css="footer {visibility: hidden}")

if __name__ == "__main__":
    iface.launch()