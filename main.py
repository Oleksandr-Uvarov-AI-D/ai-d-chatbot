from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
import time
import json
import asyncio
from contextlib import asynccontextmanager
from supabase import create_client, Client
from util import get_today_date, extract_json 
from init_azure import get_agents, make_message, get_message_list, create_thread, run_agent
from cal_com_methods import try_to_make_an_appointment

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(save_finished_threads())
    yield

    # cleanup on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Allow frontend (JavaScript in browser) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    # allow_origins=["https://widget-code.onrender.com"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_data, agent_summary, agent_summary_thread = get_agents()


# Store the last message's time for each thread.
ONGOING_THREADS = {}

# How much time a user has to respond before the chat is archived (in seconds)
time_limit_user_message = 30

async def save_finished_threads():
    while True:
        # Limit the number of threads to check so that it doesn't take up a lot of time
        threads_to_check = 4
        # making a list so that the changes are not made during the iteration
        threads_to_remove = []

        for thread_id, last_message_time in ONGOING_THREADS.items():
            if threads_to_check == 0:
                break
            
            time_now = time.time()
            if time_now - last_message_time > time_limit_user_message:
                threads_to_remove.append(thread_id)

                make_summary(thread_id)

        threads_to_check -= 1
        for thread_id in threads_to_remove:
            ONGOING_THREADS.pop(thread_id, None)

        await asyncio.sleep(30)


def insert_chatbot_message(thread_id, table_name, chatbot_type="data"):
    """Function that gets a chatbot message and
    inserts it into supabase database."
    
    Args:
        thread_id: thread id of the conversation in question
        table_name: supabase table to where the data is going to be sent
        json_msg: if set to True, the format of message is going to be sent in JSON

    Returns:
        Dict: A dictionary consisting of the role (assistant/chatbot in this case), the message, and the thread id.
    """

    messages = get_message_list(thread_id)
    
    for message in reversed(messages):
        if message.role == "assistant" and message.text_messages:
            message_to_insert = message.text_messages[-1].text.value
            try:
                message_to_insert = extract_json(message_to_insert)

                # print("message_to_insert", message_to_insert)
                # print(type(message_to_insert))

                if chatbot_type == "summary":
                    response = (
                        supabase.table(table_name)
                        .insert(message_to_insert)
                        .execute()
                    )
                    return None
                else:
                    msg = message_to_insert["message"]
                    response = (
                        supabase.table(table_name)
                        .insert(msg)
                        .execute()
                    )
                    print("chatbot type: data", "msg: ", msg)
                    return {"role": "assistant", "message": message_to_insert, "thread_id": thread_id}

            except ValueError:
                    response = (
                        supabase.table(table_name)
                        .insert(message_to_insert)
                        .execute()
                    )
                    return {"role": "assistant", "message": message_to_insert, "thread_id": thread_id}
    
    return {"role": "assistant", "message": "No response", "thread_id": thread_id}

@app.get("/health")
async def root():
    return {"status": "ok"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def home():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.get("/chat", response_class=HTMLResponse)
def home_chat():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.post("/start")
async def give_thread_id(request: Request):
    data = await request.json()
    user_input = data["message"]

    # Creating a thread for a new user
    thread = create_thread()

    # Telling the bot today's date so it doesn't make mistakes when reserving an appointment.
    # Executed every time a conversation is started so that it is relevant for every conversation.
    today = get_today_date()

    make_message(thread.id, "user", f"System message: Vandaag is {today[0]}, {today[1]}. Gebruik deze datum altijd als referentie")

    # In case it's an initial message when the user clicks on start a conversation
    # (In the other case, it means that the user ran out of time and starts a new conversation but with the chat already opened)
    if user_input == None:
        # Process today's date for conversation
        run = run_agent(thread.id, agent_data.id)
        return {"thread_id": thread.id}
    else:
        response_user = (
        supabase.table("chatbot_data")
        .insert({"role": "user", "message": user_input, "thread_id": thread.id})
        .execute()
    )


    ONGOING_THREADS[thread.id] = time.time() 

    # Initial message to get initial response from the chatbot
    make_message(thread.id, "user", user_input)

    run = run_agent(thread.id, agent_data.id)

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}
    

    chatbot_message =  insert_chatbot_message(thread.id, "chatbot_data")

    # response = (
    #     supabase.table("chatbot_data")
    #     .insert({"role": "assistant", "message": chatbot_message["message"], "thread_id": thread.id})
    #     .execute()
    # )
    
    return chatbot_message

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]
    user_thread_id = data["thread_id"]
    ONGOING_THREADS[user_thread_id] = time.time() 

    make_message(user_thread_id, "user", user_input)

    response_user = (
        supabase.table("chatbot_data")
        .insert({"role": "user", "message": user_input, "thread_id": user_thread_id})
        .execute()
    )

    run = run_agent(user_thread_id, agent_data.id)

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}
      
    # chatbot_message = insert_chatbot_message(user_thread_id, "chatbot_data")

    # chatbot_message = try_to_make_an_appointment(chatbot_message, user_thread_id)

    # response = (
    #     supabase.table("chatbot_data")
    #     .insert({"role": "assistant", "message": chatbot_message["message"], "thread_id": user_thread_id})
    #     .execute()
    # )

    # return chatbot_message

    chatbot_message = insert_chatbot_message(user_thread_id, "chatbot_data")

    return try_to_make_an_appointment(chatbot_message, user_thread_id)
    return try_to_make_an_appointment(chatbot_message["message"], user_thread_id)
    
@app.post("/end_conversation")
async def end_conversation(request: Request):
    data = await request.json()
    thread_id = data["thread_id"]

    ONGOING_THREADS.pop(thread_id, None)
    print(thread_id)

    make_summary(thread_id)



def make_summary(thread_id):
    # Get a conversation in JSON format
    message_list = (
        supabase.table("chatbot_data")
        .select("role, message")
        .eq("thread_id", thread_id)
        .execute()
        ).data

    print(message_list)

    conversation = "".join(f"{message['role']}: {message['message']}\n" for message in message_list)

    # Make a message with conversation as value (summary agent)
    make_message(agent_summary_thread.id, "user", conversation)

    # Pass the message onto summary agent
    run = run_agent(agent_summary_thread.id, agent_summary.id)

    insert_chatbot_message(agent_summary_thread.id, "chatbot_summary_data", "summary")

# book_cal_event("apelsin", "sashka15002@gmail.com", "+3212578167", "2025-09-08T10:00:00Z")
# book_cal_event("apelsin", "sashka15002@gmail.com", "+3212578167", "2025-09-08T10:00:00Z")

# print(get_available_slots(event_type_id, "2025-09-12T00:00:00+02:00", "2025-09-12T23:59:59+02:00", "2025-09-12T12:00:00+02:00"))
# print(get_available_slots(event_type_id, start_ts="2025-09-07T00:00:00+02:00", end_ts="2025-09-30T23:59:59+02:00", target_tz="2025-09-24T16:30:00+02:00"))
# print(get_available_slots(event_type_id, "2025-09-15T09:00:00"))
# print(get_available_slots())

# Further steps
# 1. cal.com api to make a meeting 
# 2. word documentation

# WXyT79wgf9s4R6w3


# can't reschedule

# still getting appointments 2 hours later on cal.com why
# should i point out that we're using a europe/brussels time zone?
# bubbles after start (second time)