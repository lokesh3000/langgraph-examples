from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

#1. State
class AgentState(TypedDict):
    query: str
    draft_answer: str
    feedback: List[str]
    approved: bool 
    final_answer: str

#2. Nodes
def draft_node(state: AgentState) -> AgentState:
    """Create a draft answer"""
    print("Drafting answer...")
    response = llm.invoke(f"Answer the following question concisely: {state['query']}")
    return {
        **state,
        "draft_answer": response.content
    }

def human_review_node(state: AgentState) -> AgentState:
    """
    Simulate human approval
    (In real apps: UI / API / interrupt)
    """
    print(f" Review this answer: {state['draft_answer']}")
    user_input = input("Approve? (yes/no): ").strip().lower()
    approved = user_input == "yes"
    feedback = state["feedback"]

    if not approved:
        new_feedback = input("Enter feedback for improvement: ").strip()
        feedback.append(new_feedback)
    return {
        **state,
        "approved": approved,
        "feedback": feedback
    }

def finalize_node(state: AgentState) -> AgentState:
    """Finalize approved answer"""
    print("Approved. Sending answer.")

    return {
        **state,
        "final_answer": state["draft_answer"]
    }

def revise_node(state: AgentState) -> AgentState:
    """Revise answer if rejected"""
    print("Revising answer...")
    feedback_text = ""
    for i, fb in enumerate(state["feedback"], 1):
        feedback_text += f"{i}. {fb}\n"
    llm_prompt = f"""The following answer was rejected by the user:
{state['draft_answer']} with feedback: {state['feedback'][-1]}
Please provide a revised answer."""
    response = llm.invoke(llm_prompt)
    # Answer:{state['draft_answer']}
    # Feedback:{feedback_text}
    return {
        **state,
        # "draft_answer": state["draft_answer"] + " (revised) " + response.content
        "draft_answer":  response.content
    }

#3. Router
def route(state: AgentState) -> str:
    return "finalize" if state["approved"] else "revise"

#4. Build graph
workflow = StateGraph(AgentState)

workflow.add_node("draft", draft_node)
workflow.add_node("review", human_review_node)
workflow.add_node("finalize", finalize_node)
workflow.add_node("revise", revise_node)

workflow.add_edge(START, "draft")
workflow.add_edge("draft", "review")

workflow.add_conditional_edges(
    "review",
    route,
    {
        "finalize": "finalize",
        "revise": "revise"
    }
)

workflow.add_edge("revise", "review")
workflow.add_edge("finalize", END)

app = workflow.compile()
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("tool_calling_workflow.png", "wb") as f:    
    f.write(graph_image) 
    
result = app.invoke({
    "query": "Explain LangGraph simply",
    "draft_answer":"",
    "feedback": [],
    "approved": False,
    "final_answer":""
})
print("Final Answer:",result["final_answer"])