from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables.graph import MermaidDrawMethod
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

#1. State
class ChatState(TypedDict):
    messages: List[str]
    response: str

#2. Node
def chat_node(state: ChatState) -> ChatState:
    print("Chatting with memory...")

    conversation = "\n".join(state["messages"])

    prompt = f"""
    Continue the conversation:
    {conversation}
    """
    reply = llm.invoke(prompt).content

    return {
        "messages": state["messages"]+[f"AI: {reply}"],
        "response": reply
    }

#3. Build Graph
workflow = StateGraph(ChatState)
workflow.add_node("chat", chat_node)
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)

#4.compile
app = workflow.compile()
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("chat_with_memory_workflow.png", "wb") as f:    
    f.write(graph_image) 

#5. Run multi-turn manually
state = {
    "messages": [],
    "response": ""
}

#Turn 1
state["messages"].append("User: What is LangGraph?")
print("User: What is LangGraph?")
state = app.invoke(state)
print("AI: ",state["response"])