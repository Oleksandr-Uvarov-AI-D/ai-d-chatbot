import streamlit as st
from azure.ai.projects import AIProjectClient
# from azure.identity import DefaultAzureCredential
from azure.identity import InteractiveBrowserCredential
# from azure.identity import AzureCliCredential
from azure.ai.agents.models import ListSortOrder

# -------------------------
# Azure AI Project Settings
# -------------------------

@st.cache_resource
def get_credential():
    return InteractiveBrowserCredential(tenant_id="2ccd5980-13cb-499f-a002-dd6a82c3acfb")

project = AIProjectClient(
    # credential=DefaultAzureCredential(),
    # credential=InteractiveBrowserCredential(
    #     tenant_id="2ccd5980-13cb-499f-a002-dd6a82c3acfb"
    # ),
    # credential = AzureCliCredential(),
    credential = get_credential(),
    endpoint="https://sashk-mesac3il-swedencentral.services.ai.azure.com/api/projects/sashk-mesac3il-swedencentral_project"
)

agent = project.agents.get_agent("asst_aUTsvggO0O5evxAN4oYBFykA")

# Create a conversation thread
# thread = project.agents.threads.create()

if "thread" not in st.session_state:
    st.session_state.thread = project.agents.threads.create()
thread = st.session_state.thread


# -------------------------
# Streamlit Interface
# -------------------------
st.set_page_config(page_title="RAG AI Chat", page_icon="🤖", layout="centered")
st.title("🤖 RAG AI Chat")

# Maintain chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input box
if prompt := st.chat_input("Ask me anything..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send message to Azure AI agent
    project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )

    run = project.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id
    )

    if run.status == "failed":
        answer = f"⚠️ Run failed: {run.last_error}"
    else:
        # messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        # answer = messages[-1].text_messages[-1].text.value if messages[-1].text_messages else "🤖 No response."
        messages = list(project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))
        if messages and messages[-1].text_messages:
            answer = messages[-1].text_messages[-1].text.value
        else:
            answer = "🤖 No response."


    # Add AI response
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
