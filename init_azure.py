from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()



credential=DefaultAzureCredential()

project = AIProjectClient(
    credential=credential,
    endpoint=os.getenv("AI_D_PROJECT_ENDPOINT")
)


agent_data = project.agents.get_agent(os.getenv("AGENT_DATA_ID"))
agent_summary = project.agents.get_agent(os.getenv("AGENT_SUMMARY_ID"))
agent_summary_thread = project.agents.threads.create()

def get_agents():
    return agent_data, agent_summary, agent_summary_thread


def make_message(thread_id, role, input_message):
    message = project.agents.messages.create(
    thread_id=thread_id,
    role=role,
    content=input_message)


def get_message_list(thread_id):
    messages = list(project.agents.messages.list(
        thread_id=thread_id,
        order=ListSortOrder.ASCENDING
        ))
    
    return messages

def create_thread():
    return project.agents.threads.create()
    

def run_agent(thread_id, agent_id):
    runs = list(project.agents.runs.list(thread_id=thread_id))
    # print(len(runs) != 0)
    # print(list(runs))
    if len(list(runs)) != 0:
        # print(len(list(runs)) != 0)
        # print(len(list(runs)))
        latest_run = list(runs)[0]
        # print("working")
        # for run in runs:
        #     print(run.created_at)

        while True:
            latest_run = project.agents.runs.get(
                thread_id=thread_id,
                run_id=latest_run.id
            )
            if latest_run.status in ("in_progress", "queued"):
                asyncio.sleep(0.5)
            else:
                break

    run = project.agents.runs.create_and_process(
        thread_id=thread_id,
        agent_id=agent_id
    )

    return run


