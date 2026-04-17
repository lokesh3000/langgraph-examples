from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.runnables.graph import MermaidDrawMethod
from langchain_core.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

class AgentState(TypedDict):
    """State for the agent."""
    query: str
    thought: str
    action: str
    observation: str
    final_answer: str

#2. Define Agent Node
def search_tool(query: str) -> str:
    """A simple search tool that returns a string result."""
    return f"Search results for '{query}': Langgraph is a framework for building agents"
    
def calculator_tool(expression: str) -> str:
    """A simple calculator tool that evaluates basic math expressions."""
    try:
        return str(eval(expression))
    except:
        return "error"

#3. Nodes
def think_node(state: AgentState) -> AgentState:
    """
    LLM decides next action
    """
    prompt = f"""
    You are an agent. Decide next step:
    Query: {state['query']}
    Previous observqtion: {state['observation']}
    Choose one:
    - search
    - calculate
    - finish

    Respond with one word.
    """

    action = llm.invoke(prompt).content[0]['text'].strip().lower()
    print(f" Thought -> {action}")

    return {
        **state,
        "action": action
    }

def act_node(state: AgentState) -> AgentState:
    """
    Executes tool based on action
    """
    action = state["action"]

    if action=="search":
        result = search_tool(state["query"])
    elif action == "calculate":
        result = calculator_tool(state["query"])
    else:
        result = "No action"
    
    print(f"Action -> {action}")
    print(f"Observation -> {result}")

    return {
        **state,
        "observation":result
    }

def answer_node(state: AgentState) -> AgentState:
    """
    Final answer
    """
    response = llm.invoke(
        f"Answer the query using this info: {state['observation']}"
    ).content

    return {
        **state,
        "final_answer": response
    }

#4. Router
def route(state: AgentState) -> str:
    if state["action"] == "finish":
        return "answer"
    return "act"

#5. Build graph
workflow = StateGraph(AgentState)
workflow.add_node("think", think_node)
workflow.add_node("act",act_node)
workflow.add_node("answer", answer_node)

workflow.add_edge(START,"think")

workflow.add_conditional_edges(
    "think",
    route,
    {
        "act": "act",
        "answer": "answer"
    }
)

workflow.add_edge("act","think")
workflow.add_edge("answer",END)

app = workflow.compile()

graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("simple_react_agent_workflow.png", "wb") as f:    
    f.write(graph_image)

result = app.invoke({
    "query": "What is LangGraph?",
    "thought": "",
    "action": "",
    "observation": "",
    "final_answer": ""
})

print("Final Answer:", result["final_answer"][0]['text'])