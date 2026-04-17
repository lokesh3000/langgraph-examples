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
    query: str
    research: str
    analysis: str
    final_answer: str

def researcher(state: AgentState) -> AgentState:
    print("Researching...")
    response = llm.invoke(f"Research the following query and provide key findings: {state['query']}")
    return {
        **state,
        "research": response.content
    }

def analyst(state: AgentState) -> AgentState:
    print("Analyst processing...")
    response = llm.invoke(f"""Analyze the following research and extract key insights: {state['research']}""")
    return {
        **state,
        "analysis": response.content
    }

def writer(state: AgentState) -> AgentState:
    print("Writer creating final answer...")
    response = llm.invoke(f"""Using the following analysis, write a clear and concise final: {state['analysis']}""")
    return {
        **state,
        "final_answer": response.content
    }

workflow = StateGraph(AgentState)

workflow.add_node("researcher", researcher)
workflow.add_node("analyst", analyst)
workflow.add_node("writer", writer)

workflow.add_edge(START, "researcher")
workflow.add_edge("researcher", "analyst")
workflow.add_edge("analyst","writer")
workflow.add_edge("writer",END)

app = workflow.compile()
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("multi_agent_workflow.png", "wb") as f:    
    f.write(graph_image)

result = app.invoke({
    "query": "What is the state of AI?",
    "research":"",
    "analysis":"",
    "final_answer":""
})

print("Final Answer: ", result["final_answer"])
 