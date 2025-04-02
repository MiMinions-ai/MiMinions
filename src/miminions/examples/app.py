import streamlit as st
from supplier import *

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "voice" not in st.session_state:
    st.session_state.voice = None
if "sys_msg" not in st.session_state:
    st.session_state.sys_msg = App_state["sys_msg"]

# Set page config
st.set_page_config(
    page_title="MiMinions.ai",
    page_icon="🤖",
    layout="wide"
)

# Sidebar for settings
with st.sidebar:
    st.title("Settings")
    
    # Background/system message settings
    st.subheader("Background Settings")
    background = st.text_area(
        "Current background",
        value=st.session_state.sys_msg[0]["content"],
        height=150
    )
    
    if st.button("Update Background"):
        st.session_state.sys_msg[0].update({"content": background})
        st.success("Background updated!")
    
    # Voice selection
    st.subheader("Voice Settings")
    voices = [v["Name"] for v in get_voices()]
    selected_voice = st.selectbox("Select Voice", voices)
    if selected_voice:
        App_state.update({"voice": selected_voice})

# Main chat interface
st.title("MiMinions.ai Chat")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to say?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get bot response
    with st.chat_message("assistant"):
        response = send_chat(prompt, st.session_state.messages)
        st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Add text-to-speech button
        if st.button("Play Response"):
            audio = text_to_audio([{"role": "assistant", "content": response}])
            st.audio(audio)

# Voice input
st.subheader("Voice Input")
audio_file = st.audio_recorder()
if audio_file:
    text = translate(audio_file)
    if text:
        st.session_state.messages.append({"role": "user", "content": text})
        with st.chat_message("user"):
            st.write(text)
        
        # Get bot response
        with st.chat_message("assistant"):
            response = send_chat(text, st.session_state.messages)
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Add text-to-speech button
            if st.button("Play Response"):
                audio = text_to_audio([{"role": "assistant", "content": response}])
                st.audio(audio)

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()