from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables.graph import MermaidDrawMethod
import os

os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

#1. Define states
class NumberState(TypedDict):
    number: int
    result: str

#2. Define nodes
def check_number(state: NumberState) -> NumberState:
    """Decide if the number is even or odd."""
    print(f"Checking number: {state['number']}")
    return state

def even_node(state: NumberState) -> NumberState:
    """Handle even numbers."""
    return {
        **state,
        "result": f"{state['number']} is even."
    }

def odd_node(state: NumberState) -> NumberState:
    """Handle odd numbers."""
    return {
        **state,
        "result": f"{state['number']} is odd."
    }

#3. Route (this is your if-else logic)
def route(state: NumberState) -> str:
    """Route to the correct node based on even or odd."""
    if state["number"] % 2 == 0:
        return "even"
    else:
        return "odd"

#4. Build the graph
workflow = StateGraph(NumberState)
workflow.add_node("check", check_number)
workflow.add_node("even", even_node)
workflow.add_node("odd", odd_node)
workflow.add_edge(START, "check")
workflow.add_conditional_edges(
    "check",  #conditional node
    route, #routing function
    {
        "even": "even",
        "odd": "odd"
    }
)
workflow.add_edge("even", END)
workflow.add_edge("odd", END)

#5. Compile the graph
app = workflow.compile()

# Generate and save the graph visualization
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("even_odd_workflow.png", "wb") as f:    
    f.write(graph_image)

#6. Run the graph
result = app.invoke({
        "number": 6,
        "result": ""
    })
print("\n Final Result:", result)
