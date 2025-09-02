from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
import time
import json
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


app = FastAPI()

# Allow frontend (JavaScript in browser) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

credential=DefaultAzureCredential()

project = AIProjectClient(
    credential=credential,
    endpoint=os.getenv("AI_D_PROJECT_ENDPOINT")
)



agent_data = project.agents.get_agent(os.getenv("AGENT_DATA_ID"))
agent_summary = project.agents.get_agent(os.getenv("AGENT_SUMMARY_ID"))
agent_summary_thread = project.agents.threads.create()


# Store the last message's time for each thread.
ONGOING_THREADS = {}
# Last time the ongoing threads have been checked. (Used to not check it very often but after a specific time.)
last_time_checked = time.time()

# How often the threads are checked for being finished (in seconds)
update_rate = 30

# How much time a user has to respond before the chat is archived (in seconds)
time_limit_user_message = 30

def insert_chatbot_message(thread_id, table_name, json_msg=False):
    """Function that gets a chatbot message and
    inserts it into supabase database / displays it in the widget for the user.
    
    Args:
        thread_id: thread id of the conversation in question
        table_name: supabase table to where the data is going to be sent
        json_msg: if set to True, the format of message is going to be sent in JSON

    Returns:
        Dict: A dictionary consisting of the role (assistant/chatbot in this case), the message, and the thread id.
    """

    messages = list(project.agents.messages.list(
        thread_id=thread_id,
        order=ListSortOrder.ASCENDING
        ))
    
    for message in reversed(messages):
        if message.role == "assistant" and message.text_messages:
            message_to_insert = message.text_messages[-1].text.value
            print(message_to_insert)
            if json_msg:
                message_to_insert = json.loads(message_to_insert)
                response = (
                    supabase.table(table_name)
                    .insert(message_to_insert)
                    .execute()
                )
                return None
            else:
                response = (
                    supabase.table(table_name)
                    .insert({"role": "assistant", "message": message_to_insert, "thread_id": thread_id})
                    .execute()
                )
                return {"role": "assistant", "message": message_to_insert, "thread_id": thread_id}
    
    return {"role": "assistant", "message": "No response", "thread_id": thread_id}




def save_finished_threads():
    global last_time_checked
    time_now = time.time()
    # Limit the number of threads to check so that it doesn't take up a lot of time
    threads_to_check = 4
    # making a list so that the changes are not made during the iteration
    threads_to_remove = []

    if time_now - last_time_checked > update_rate:
        last_time_checked = time_now
        for thread_id, last_message_time in ONGOING_THREADS.items():
            if threads_to_check == 0:
                break
            
            if time_now - last_message_time > time_limit_user_message:
                threads_to_remove.append(thread_id)

                # Get a conversation in JSON format
                conversations = (
                    supabase.table("chatbot_data")
                    .select("role, message")
                    .eq("thread_id", thread_id)
                    .execute()
                    ).data
                
                
                # conversations_str = "conversations_str value: ".join(f"{conv['role']}: {conv['message']}" for conv in conversations)
                conversations_str = "".join(f"{conv['role']}: {conv['message']}" for conv in conversations)
                

                # Make a message with conversation as value (summary agent)
                message = project.agents.messages.create(
                    thread_id=agent_summary_thread.id,
                    role="user",
                    content=conversations_str
                )

                # Pass the message onto summary agent
                run = project.agents.runs.create_and_process(
                    thread_id=agent_summary_thread.id,
                    agent_id=agent_summary.id
                )

                # messages = list(project.agents.messages.list(
                #     thread_id=agent_summary_thread.id,
                #     order=ListSortOrder.ASCENDING
                #     ))

                # for message in reversed(messages):
                #     if message.role == "assistant" and message.text_messages:
                #         # At this point, message value is an str that needs to be converted into JSON
                #         message_json = json.loads(message.text_messages[-1].text.value)
                #         response = (
                #             supabase.table("chatbot_summary_data")
                #             .insert(message_json)
                #             .execute()
                #         )
                #         break

                # return value is not used in this case because the idea here
                # is to only send data (summary of the conversation) to supabase
                insert_chatbot_message(agent_summary_thread.id, "chatbot_summary_data", True)

        threads_to_check -= 1
        for thread_id in threads_to_remove:
            ONGOING_THREADS.pop(thread_id, None)


@app.get("/health")
async def root():
    return {"status": "ok"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def home():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.get("/chat", response_class=HTMLResponse)
def home():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.post("/start")
async def give_thread_id(request: Request):
    data = await request.json()
    user_input = data["message"]
    # In case it's an initial message when the user clicks on start a conversation
    # (In the other case, it means that the user ran out of time and starts a new conversation but with the chat already opened)
    if user_input == None:
        user_input = "Hallo"

    # Creating a thread for a new user
    thread = project.agents.threads.create()

    ONGOING_THREADS[thread.id] = time.time() 

    # Initial message to get initial response from the chatbot
    message = project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    run = project.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_data.id
    )

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}
    
    return insert_chatbot_message(thread.id, "chatbot_data")

    # messages = list(project.agents.messages.list(
    # thread_id=thread.id,
    # order=ListSortOrder.ASCENDING
    # ))

    # for message in reversed(messages):
    #     if message.role == "assistant" and message.text_messages:
    #         response = (
    #             supabase.table("chatbot_data")
    #             .insert({"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": thread.id})
    #             .execute()
    #         )     
    #         return {"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": thread.id}

    # return {"role": "assistant", "message": "No response", "thread_id": thread.id}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]
    user_thread_id = data["thread_id"]
    ONGOING_THREADS[user_thread_id] = time.time() 

    message = project.agents.messages.create(
        thread_id=user_thread_id,
        role="user",
        content=user_input
    )

    response_user = (
        supabase.table("chatbot_data")
        .insert({"role": "user", "message": user_input, "thread_id": user_thread_id})
        .execute()
    )

    run = project.agents.runs.create_and_process(
        thread_id=user_thread_id,
        agent_id=agent_data.id
    )

    save_finished_threads()

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}
      
    return insert_chatbot_message(user_thread_id, "chatbot_data")


    # Getting a list of messages
    # messages = list(project.agents.messages.list(
    #     thread_id=user_thread_id,
    #     order=ListSortOrder.ASCENDING
    # ))

    # # Last assistant message
    # for message in reversed(messages):
    #     if message.role == "assistant" and message.text_messages:
    #         # [-1] here to get the last fragment in case one assistant message contains multiple text fragments
    #         response_assistant = (
    #             supabase.table("chatbot_data")
    #             .insert({"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": user_thread_id})
    #             .execute()
    #         )

    #         return {"role": "assistant", "message": message.text_messages[-1].text.value}

    # return {"role": "assistant", "message": "No response"}


# Problems for now
# 1. How to end a conversation
    # Make a timer or check for a specific ending of a message ("Tot ziens!")?

# Done but need to make sure it works
# 1. Individual history


# Further steps
# 1. cal.com api to make a meeting 
# 2. layout fix (logo etc)

# WXyT79wgf9s4R6w3

# things to point out

# 1. When the user sends their last message, the conversation doesn't end until time runs out.
# 2. auto-reply message (could do it in both languages)



