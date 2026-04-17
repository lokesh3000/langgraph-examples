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

#1. Define Tools (@tool)
@tool
def calculator_tool(expression: str) -> str:
    """A simple calculator tool that evaluates basic math expressions."""
    try:
        return str(eval(expression))
    except:
        return f"Error in calculation"



@tool
def weather_tool(location: str) -> dict:
   """Get current weather for a city"""
   try:
       geo_url = "https://geocoding-api.open-meteo.com/v1/search"
       geo_resp = requests.get(geo_url, params={"name": location, "count": 1}, timeout=10)
       geo_data = geo_resp.json()


       if not geo_data.get("results"):
           return f"Could not find location: {location}"


       place = geo_data["results"][0]
       lat, lon = place["latitude"], place["longitude"]
       city_name = place.get("name", location)
       country = place.get("country", "")


       weather_url = "https://api.open-meteo.com/v1/forecast"
       weather_resp = requests.get(
           weather_url,
           params={
               "latitude": lat,
               "longitude": lon,
               "current_weather": True,
           },
           timeout=10,
       )


       data = weather_resp.json()
       cw = data.get("current_weather", {})


       return f"Weather in {city_name}, {country}: {cw}"
   except Exception as e:
       return f"Error fetching weather for {location}: {e}"

tools = [calculator_tool, weather_tool]

#Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

#2. State

class AgentState(TypedDict):
    query: str
    messages: List
    result: str

#3. Node (LLM decides + calls tools)
def agent_node(state: AgentState) -> AgentState:
    print("Agent thinking...")

    message = list(state["messages"])
    tool_map = {t.name: t for t in tools}

    #dynamically call tools until LLM has no more tool calls in its reponse
    while True:
        response = llm_with_tools.invoke({"messages": message})
        message.append(response)
        print("*********")
        print(f"Response Tool Calls: {response.tool.call}")
        print("*********")
        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call["tool"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]
            
            tool_fn = tool_map[tool_name]
            tool_result = tool_fn.invoke(tool_args)

            messages.append({
                "role":"tool",
                "content": str(tool_result),
                "name": tool_name,
                "tool_call_id": tool_call_id
            })
    return {
        **state,
        "messages": messages,
        "result": response.content
    }

#4. Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)

workflow.add_edge(START,"agent")
workflow.add_edge("agent",END)

app = workflow.compile()
# Generate and save the graph visualization
graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("tool_calling_workflow.png", "wb") as f:    
    f.write(graph_image)  

# print("\n--- Example 1 (Math) ---")
# result1 = app.invoke({
#     "query": "25 * 4 + 10",
#     "messages": [{"role": "user", "content": "25 * 4 + 10"}],
#     "result": ""
# })
# print("Final:", result1["result"])




print("\n--- Example 2 (Weather) ---")
result2 = app.invoke({
   "query": "What is the weather in Chennai and multiply that by 2",
   "messages": [{"role": "user", "content": "What is the weather in Chennai and multiply that by 2?"}],
   "result": ""
})
print("Final:", result2["result"])




# print("\n--- Example 3 (General) ---")
# result3 = app.invoke({
#     "query": "What is LangGraph?",
#     "messages": [{"role": "user", "content": "What is LangGraph?"}],
#     "result": ""
# })
# print("Final:", result3["result"])

 