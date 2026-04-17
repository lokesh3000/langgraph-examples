from langgraph.graph import StateGraph, MessagesState, START, END

def mock_llm(state: MessagesState):
    print("Mock LLM called with state:", state)
    return {"messages": [{"role": "ai", "content": "Hello, how can I help you?"}]}

graph = StateGraph(MessagesState)
graph.add_node("mock_llm", mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

graph_image = graph.get_graph().draw_mermaid_png()
with open("examples/example1/first-workflow.py.png", "wb") as f:
    f.write(graph_image)

result = graph.invoke({"messages": [{"role": "user", "content": "Hi!"}]})
print("*"*50)
print("Result:", result)