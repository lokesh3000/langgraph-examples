from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
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
    messages: Annotated[List, add_messages]

#4. Agent Node
def agent_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

#5. Control Flow
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

#6. Tool Node
tool_node = ToolNode(tools)

#7. Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent", 
    should_continue,
    ["tools", END]
)

workflow.add_edge("tools", "agent")
app = workflow.compile()

graph_image = app.get_graph().draw_mermaid_png(
    draw_method=MermaidDrawMethod.PYPPETEER
    )
with open("tool_calling_workflow.png", "wb") as f:    
    f.write(graph_image)

result = app.invoke({
    "messages": [
        {
            "role": "user",
            "content": "What's the weather in Chennai and multiply it by 2?"
        }
    ]
})  

print("Final Result: ")
print(result["messages"][-1].content)