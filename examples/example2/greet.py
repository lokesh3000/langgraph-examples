from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables.graph import MermaidDrawMethod
import os

os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

#1. Define states
class SimpleState(TypedDict):
    message: str

#2. Define nodes
def greet_node(state: SimpleState) -> SimpleState:
    print("User said:", state["message"])
    return {"message": f"Hello! You said: {state['message']}!"}

def finish_node(state: SimpleState) -> SimpleState:
    print("Final response ready")
    return state

#3. Build the graph
workflow = StateGraph(SimpleState)

workflow.add_node("greet", greet_node)
workflow.add_node("finish", finish_node)

workflow.add_edge(START, "greet")
workflow.add_edge("greet", "finish")
workflow.add_edge("finish", END)

#4. Compile the graph
app = workflow.compile()

# Generate and save the graph visualization
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("greet_workflow.png", "wb") as f:
    f.write(graph_image)

#5. Run the graph
result = app.invoke({"message": "Hi there!"})
print("\n Final Result:", result)