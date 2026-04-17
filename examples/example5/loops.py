from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables.graph import MermaidDrawMethod
import os
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

# 1. Define shared state
class NumberState(TypedDict):
    number: int
    is_valid: bool
    attempts: int

# 2. Nodes
def validate_number(state: NumberState) -> NumberState:
    """Check if number is valid (positive number)."""
    num = state["number"]
    print(f"Checking: {num}")

    is_valid = num > 0
    return {
        **state,
        "is_valid": is_valid,
        "attempts": state["attempts"] + 1
    }

def retry_node(state: NumberState) -> NumberState:
    """Simulate retry (fixing th input)."""
    print("Invalid number. Retrying...")
    new_number = state["number"] + 5
    return {
        **state,
        "number":new_number
    }

def success_node(state: NumberState) -> NumberState:
    """Final success node."""
    print("Valid number found!")
    return state

# 3. Router (loop decision)

def route(state: NumberState) -> str:
    if state["is_valid"]:
        return "success"
    else:
        return "retry"

# 4. Build the graph
workflow = StateGraph(NumberState)

workflow.add_node("validate", validate_number)
workflow.add_node("retry", retry_node)
workflow.add_node("success", success_node)

workflow.add_edge(START, "validate")

workflow.add_conditional_edges(
    "validate",
    route,
    {
        "success": "success",
        "retry": "retry"
    }
)

#This is the important part (loop) 
workflow.add_edge("retry", "validate")
workflow.add_edge("success", END)

# 5. Compile the graph
app = workflow.compile()

# Generate and save the graph visualization
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("loops_workflow.png", "wb") as f:    
    f.write(graph_image)    

# 6. Run the graph
result = app.invoke({
    "number": -10,
    "is_valid": False,
    "attempts": 0
})

print("\n Final State:", result)

