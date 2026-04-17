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

LONG_TERM_MEMORY = ["User prefers simple explanations"]

DOCUMENTS = {
    "solar system": "The Solar System is a gravitationally bound system of the system of the Sun and the",
    "rag": "RAG combines retrieval with generation using externa; lnowledge."
}

#1. State
class AgentState(TypedDict):
    query: str
    memory: List[str]
    context: str
    answer: str
    is_good: bool
    attempts: int

#2. Nodes
def retrieve_memory(state: AgentState) -> AgentState:
    print("Retrieving memory...")
    return {
        **state,
        "memory": LONG_TERM_MEMORY
    }

def retrieve_docs(state: AgentState) -> AgentState:
    print("Retrieving documents....")
    query = state["query"].lower()
    context = ""
    for key, value in DOCUMENTS.items():
        if key in query:
            context += value + "\n"
    
    if not context:
        context = "No relevant documents found."
    
    return {
        **state,
        "context": context
    }

def generate_node(state: AgentState) -> AgentState:
    print("Generating answer...")

    memory_text = "\n".join(state["memory"])

    prompt = f"""
    User preferences:
    {memory_text}

    Context:
    {state['context']}

    Question:
    {state['query']}

    Answer clearly.
    """

    answer = llm.invoke(prompt).content

    return {
        **state,
        "answer": answer,
        "attempts": state["attempts"]+1
    }

def evaluate_node(state: AgentState) -> AgentState:

    """Evaluate answer quality using LLM"""
    print("Evaluating answer")

    prompt = f"""
    Question: {state['query']}
    Answer: {state['answer']}
    Is this answer good and complete?

    """
    result = llm.invoke(prompt)
    print(f"Evaluation: is_good={result.is_good}, feedback={result.feedback}")
    return {
        **state,
        "is_good": result.is_good,
        "feedback": result.feedback
    }

#3. Router
def route(state: AgentState) -> str:
    if state["is_good"] or state["attempts"] >= 3:
        return "end"
    return "retry"

# 4. Build graph


workflow = StateGraph(AgentState)


workflow.add_node("memory", retrieve_memory)
workflow.add_node("retrieve", retrieve_docs)
workflow.add_node("generate", generate_node)
workflow.add_node("evaluate", evaluate_node)


workflow.add_edge(START, "memory")
workflow.add_edge("memory", "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "evaluate")


workflow.add_conditional_edges(
   "evaluate",
   route,
   {
       "retry": "generate",
       "end": END
   }
)




# 5. Compile
app = workflow.compile()
# Generate and save the graph visualization
graph_image = app.get_graph().draw_mermaid_png(
   draw_method=MermaidDrawMethod.PYPPETEER
)
with open("rag_workflow.png", "wb") as f:
   f.write(graph_image)




# 6. Run


result = app.invoke({
   "query": "What is Solar System?",
   "memory": [],
   "context": "",
   "answer": "",
   "is_good": False,
   "attempts": 0
})


print("\nFinal Answer:", result["answer"])
print("Attempts:", result["attempts"])

