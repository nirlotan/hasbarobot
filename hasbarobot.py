import os
import re
import openai
import streamlit as st
import random
import time
from time import sleep
import hmac

##### Password Protection #####

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the passward is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.



##### App Auxiliary Functions #####

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
TEXT_CHAT_ASSISTANT_ID = st.secrets["TEXT_CHAT_ASSISTANT_ID"]
LINKS_CHAT_ASSISTANT_ID = st.secrets["LINKS_CHAT_ASSISTANT_ID"]

class openai_chat():
    def __init__(self, assistant_id):
        self.client = openai.OpenAI(api_key= OPENAI_API_KEY )
        self.assistant_id = assistant_id
        self.assistant = self.client.beta.assistants.retrieve( self.assistant_id )
        self.thread = self.client.beta.threads.create()
        self.check_every_ms: float = 1_000.0
        self.run = None

    def send_message(self, text):
        gpt_message = self.client.beta.threads.messages.create(
            thread_id = self.thread.id,
            role="user",
            content=text
        )
        
        if self.run == None:
            self.run = self.client.beta.threads.runs.create(
                thread_id = self.thread.id,
                assistant_id = self.assistant_id,
            )

    def remove_brackets(self, text):
        return re.sub(r'【.+?】', '', text)

    def wait_for_run(self):
        in_progress = True
        while in_progress:
            run = self.client.beta.threads.runs.retrieve(self.run.id, thread_id=self.thread.id)
            in_progress = run.status in ("in_progress", "queued")
            if in_progress:
                sleep(self.check_every_ms / 1000)
        return run


    def get_response(self):

        self.wait_for_run()

        answer = ""
        for retry in range(1,8):

            run = self.client.beta.threads.runs.retrieve(
                thread_id = self.thread.id,
                run_id = self.run.id
            )

            gpt_messages = self.client.beta.threads.messages.list(
                run.thread_id, order="desc"
            )
            new_messages = [msg for msg in gpt_messages if msg.run_id == run.id]

            Any = object()

            answer: Any = [
                msg_content for msg in new_messages for msg_content in msg.content
            ]
            if all(
                isinstance(content, openai.types.beta.threads.MessageContentText)
                for content in answer
            ):
                answer = "\n".join(content.text.value for content in answer)

            if answer !="":
                break

        return self.remove_brackets(answer)

##### App Main #####


#@st.cache_resource
def init_chat(id):
    return openai_chat(id)

st.title("Hasbarobot 🤖")
aic_text = init_chat(TEXT_CHAT_ASSISTANT_ID)
aic_links = init_chat(LINKS_CHAT_ASSISTANT_ID)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Type the message you want to reply to..."):

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    aic_text.send_message(prompt)

    response = aic_text.get_response()

    if response != "":
        aic_links.send_message(response)
        response_link = aic_links.get_response()
        answer = f"{response} {response_link}"
    else:
        answer = "Something went wrong, please try again..."

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Simulate stream of response with milliseconds delay
        for chunk in answer.split():
            full_response += chunk + " "
            time.sleep(0.05)
            # Add a blinking cursor to simulate typing
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})