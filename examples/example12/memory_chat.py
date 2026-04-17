from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.runnables.graph import MermaidDrawMethod
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"
LONG_TERM_MEMORY = []

#1. State
class MemoryState(TypedDict):
    query: str
    memory: List[str]
    response: str

#2. Nodes
def retrieve_memory(state: MemoryState) -> MemoryState:
    """Fetch stored user preferences"""
    print("Retrieving memory...")
    return {
        **state,
        "memory": LONG_TERM_MEMORY
    }

def generate_response(state: MemoryState) -> MemoryState:
    """Generate answer using memory"""
    print("Generating response...")
    memory_text = "\n".join(state["memory"])

    prompt = f"""
    User preferences:
    {memory_text}

    Answer the question accordingly.
    Question: {state['query']}
    """

    answer = llm.invoke(prompt).content
    return {
        **state,
        "response": answer
    }

def store_memory(state: MemoryState) -> MemoryState:
    """Store useful long-term info"""
    print("Checking if we should store memory...")

    query = state["query"].lower()

    # if "simple" in query:
    #     memory = "User prefers simple explanations"
    #     if memory not in LONG_TERM_MEMORY:
    #         LONG_TERM_MEMORY.append(memory)

    #connect to llm asking it to detect preference from query and ask it to return the preference in a single sentence
    prompt = f"""Based on the following user query, determine if there are any preferences or 
    important information that should be remembered for future interactions. If so, summarize it in a single sentence. 
    User query: {state['query']}
    """
    memory = llm.invoke(prompt).content.strip()

    if memory not in LONG_TERM_MEMORY:
        LONG_TERM_MEMORY.append(memory)

    return state

#3. Build graph
workflow = StateGraph(MemoryState)

workflow.add_node("retrieve", retrieve_memory)
workflow.add_node("generate", generate_response)
workflow.add_node("store", store_memory)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "store")
workflow.add_edge("store", END)
app = workflow.compile() 
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("memory_workflow.png", "wb") as f:    
    f.write(graph_image) 

while True:
    user_input = input("You: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("quit","exit"):
        print("Goodbye!")
        break

    result = app.invoke({
        "query":user_input,
        "memory":[],
        "response": ""
    })
    print(f"\nAssistant: {result['response']}")
    print(f"[Memory: {LONG_TERM_MEMORY}]")