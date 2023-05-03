import gradio as gr
from supplier import *

background_examples=[
    "This is a friendly chatbot with humour.", # casual setting
    "This is the first date between virtual human and real human.", # romantic setting
    "We are at the mideval castle, I am talking to my chatbot donkey.", # fantasy setting
]

with gr.Blocks() as settings:
    with gr.Row():
        background = gr.TextArea(sys_msg[0]["content"],lines=5,label="Current background")
        with gr.Column():
            def update_sys(text):
                sys_msg[0].update({"content":text})
                return text
            
            background_edit = gr.Textbox(placeholder="change the background here",label="update background",lines = 5)
            background_edit.submit(update_sys,background_edit,background)
            with gr.Row():
                clear = gr.Button("Clear")
                submit = gr.Button("Submit")

            gr.Examples(background_examples,background_edit,label="Examples")
            clear.click(lambda:None,None,background_edit,queue=False)
            submit.click(update_sys,background_edit,background,queue=False)
            
with gr.Blocks() as chat_window:
    with gr.Column():
        chatbot = gr.Chatbot(initial_msg)
        msg = gr.Textbox()
        clear = gr.Button("Clear")

    msg.submit(send_chat,[msg,chatbot],[msg,chatbot])
    clear.click(lambda:None,None,chatbot,queue=False)

iface = gr.TabbedInterface([chat_window,settings],[["Chatbot","Settings"]],"bottom",title="Chatbot",description="A chatbot with GPT-3.5 Turbo")

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0")