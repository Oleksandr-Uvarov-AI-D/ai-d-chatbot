from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import os

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint="https://sashk-mesac3il-swedencentral.services.ai.azure.com/api/projects/sashk-mesac3il-swedencentral_project")

agent = project.agents.get_agent("asst_aUTsvggO0O5evxAN4oYBFykA")

thread = project.agents.threads.create()
print(f"Created thread, ID: {thread.id}")

while True:
    user_input = input("What do you want to ask from AI? ")

    if user_input == "Stop the conversation.":
        break

    message = project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        # content="What do you know about AI-D? Who are the cofounders?"
        # content="Who does AI-D team consist of?"
        content=user_input
    )

    run = project.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id)

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
    else:
        messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

        for message in messages:
            if message.text_messages:
                print(f"{message.role}: {message.text_messages[-1].text.value}")