from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from langchain_core.runnables.graph import MermaidDrawMethod
import os
from dotenv import load_dotenv

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "1263111"

class EvalResult(BaseModel):
    is_good: bool
    feedback: str
eval_llm = llm.with_structured_output(EvalResult)

#1. State
class EvalState(TypedDict):
    query: str
    answer: str
    is_good: bool
    feedback: str
    attempts: int

#2. Nodes
# This example demonstrates a simple self-evaluation loop where the LLM generates an answer, evaluates its quality, and if the answer is not good, it provides feedback for improvement and retries up to 3 attempts.
def generate_node(state: EvalState) -> EvalState:
    """Generate answer"""
    print("Generating answer...")
    answer = llm.invoke(state["query"]).content.strip()
    return {
        **state,
        "answer": answer,
        "attempts": state["attempts"]+1
    }

#if feedback is no, we can ask the llm to provide feedback on what is missing in the answer and store that feedback in the state for future improvement and improve the answer iteratively until the answer is good or we reach a max number of 2 attempts
def evaluate_node(state: EvalState) -> EvalState:

    """Evaluate answer quality using LLM"""
    print("Evaluating answer")

    prompt = f"""
    Question: {state['query']}
    Answer: {state['answer']}
    Is this answer good and complete?

    """
    result: EvalResult = eval_llm.invoke(prompt)
    print(f"Evaluation: is_good={result.is_good}, feedback={result.feedback}")
    return {
        **state,
        "is_good": result.is_good,
        "feedback": result.feedback
    }

#3. Router
def route(state: EvalState) -> str:
    if state["is_good"] or state["attempts"] >= 3:
        return "end"
    return "retry"

#4. Build Graph
workflow = StateGraph(EvalState)

workflow.add_node("generate", generate_node)
workflow.add_node("evaluate", evaluate_node)

workflow.add_edge(START, "generate")
workflow.add_edge("generate", "evaluate")

workflow.add_conditional_edges(
    "evaluate",
    route,
    {
        "retry": "generate",
        "end": END
    }
)

#5. Compile
app = workflow.compile()
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("eval_workflow.png", "wb") as f:    
    f.write(graph_image) 

#6. Run
result = app.invoke({
    "query": "Explain Quantum Physics in detail",
    "answer": "",
    "is_good": False,
    "attempts": 0
})

print("Final Answer: ",result["answer"])
print("Attempts: ",result["attempts"])
# print("Feedback: ", result["feedback"])