# ============================================
# COMPLETE IMPORTS
# ============================================
from typing import Annotated, Literal, TypedDict
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


# ============================================
# 1. STATE DEFINITION
# ============================================
class AgentState(TypedDict):
   """Schema for the agent's memory across nodes"""
   topic: str
   content_draft: str
   critique: str
   critique_score: int
   human_feedback: str
   revision_count: int
   final_output: str


# ============================================
# 2. NODE DEFINITIONS
# ============================================


def research_node(state: AgentState) -> Command[Literal["planner_node"]]:
   """Simulates research phase - in production, this would call search APIs"""
   print(f"\n🔍 RESEARCH NODE")
   print(f"   Researching topic: {state['topic']}")
  
   # Simulate research
   research_data = f"Latest trends and insights about {state['topic']}"
  
   return Command(
       update={
           "content_draft": f"Research completed: {research_data}",
           "revision_count": 0
       },
       goto="planner_node"
   )


def planner_node(state: AgentState) -> Command[Literal["critic_node"]]:
   """
   Generates or refines content strategy
   Uses feedback from critic to improve drafts
   """
   revision = state.get("revision_count", 0)
   print(f"\n📝 PLANNER NODE (Revision #{revision + 1})")
  
   # Initial draft
   if revision == 0:
       draft = f"""
       Content Strategy for {state['topic']}:
       1. Social media campaign on LinkedIn and Twitter
       2. Blog post series (3 articles)
       3. Email newsletter to existing subscribers
       """
   else:
       # Refine based on feedback
       feedback = state.get("human_feedback") or state.get("critique", "")
       draft = f"""
       REFINED Strategy for {state['topic']}:
       1. Multi-platform social campaign (LinkedIn, Twitter, Reddit)
       2. In-depth blog series with SEO optimization
       3. Targeted email segments based on user behavior
       4. Partnership outreach to micro-influencers
      
       Improvements addressing: {feedback}
       """
  
   print(f"   Generated draft (length: {len(draft)} chars)")
  
   return Command(
       update={
           "content_draft": draft,
           "revision_count": revision + 1
       },
       goto="critic_node"
   )


def critic_node(state: AgentState) -> Command[Literal["planner_node", "approval_gate"]]:
   """
   Evaluates content quality
   Implements CYCLIC routing - can loop back to planner
   """
   print(f"\n🎯 CRITIC NODE")
  
   draft = state["content_draft"]
   revision = state["revision_count"]
  
   # Simulate AI critique logic
   if revision == 1:
       score = 6
       critique = "Missing competitive analysis and metrics. Too generic."
       should_refine = True
   elif revision == 2:
       score = 7
       critique = "Better, but needs more concrete KPIs and timeline."
       should_refine = True
   else:
       score = 9
       critique = "Comprehensive strategy with clear metrics. Ready for approval."
       should_refine = False
  
   print(f"   Score: {score}/10")
   print(f"   Critique: {critique}")
  
   # CONDITIONAL ROUTING - This creates the cycle
   if should_refine and revision < 3:
       print("   ❌ Routing back to PLANNER for refinement")
       return Command(
           update={
               "critique": critique,
               "critique_score": score
           },
           goto="planner_node"  # CYCLIC EDGE
       )
   else:
       print("   ✅ Routing to APPROVAL GATE")
       return Command(
           update={
               "critique": critique,
               "critique_score": score
           },
           goto="approval_gate"  # FORWARD EDGE
       )


def approval_gate(state: AgentState) -> Command[Literal["publisher_node", "planner_node"]]:
   """
   HUMAN-IN-THE-LOOP node using interrupt()
   Pauses execution to wait for human approval
   """
   print(f"\n⏸️  APPROVAL GATE - WAITING FOR HUMAN INPUT")
  
   # Prepare payload for human review
   review_payload = {
       "message": "🚨 Human approval required!",
       "content_draft": state["content_draft"],
       "critique": state["critique"],
       "score": state["critique_score"],
       "revisions_made": state["revision_count"],
       "question": "Approve this strategy? (yes/no/feedback)"
   }
  
   # INTERRUPT - Graph execution PAUSES here
   # Returns control to the caller with review_payload
   # Waits indefinitely until Command(resume=...) is called
   human_response = interrupt(review_payload)
  
   print(f"\n✅ HUMAN RESPONDED: {human_response}")
  
   # Process human decision
   if human_response.get("action") == "approve":
       return Command(
           update={"human_feedback": "Approved by human"},
           goto="publisher_node"
       )
   elif human_response.get("action") == "reject":
       return Command(
           update={
               "human_feedback": human_response.get("feedback", "Rejected - no specific feedback")
           },
           goto="planner_node"  # Send back for another revision
       )
   else:
       # Default to rejection if unclear
       return Command(
           update={"human_feedback": "Unclear response - defaulting to rejection"},
           goto="planner_node"
       )


def publisher_node(state: AgentState):
   """
   Final execution node - publishes the approved strategy
   """
   print(f"\n🚀 PUBLISHER NODE")
   print(f"   EXECUTING FINAL STRATEGY:")
   print(f"   {state['content_draft'][:200]}...")
  
   return {
       "final_output": f"PUBLISHED: {state['content_draft']}",
       "human_feedback": state.get("human_feedback", "")
   }


# ============================================
# 3. BUILD THE GRAPH
# ============================================


print("Building graph...")
builder = StateGraph(AgentState)


# Add all nodes
builder.add_node("research_node", research_node)
builder.add_node("planner_node", planner_node)
builder.add_node("critic_node", critic_node)
builder.add_node("approval_gate", approval_gate)
builder.add_node("publisher_node", publisher_node)


# Define entry point
builder.add_edge(START, "research_node")


# Exit edge
builder.add_edge("publisher_node", END)


# Compile with checkpointer (REQUIRED for interrupts)
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)


print("✅ Graph compiled successfully!\n")


# Optional: Save the graph as an image file
try:
   graph_image = graph.get_graph().draw_mermaid_png()
   with open("agent_workflow.png", "wb") as f:
       f.write(graph_image)
   print("✅ Graph saved as 'agent_workflow.png'")
except Exception as e:
   print(f"Could not save graph visualization: {e}")


# ============================================
# 4. EXECUTION: PART 1 - RUN UNTIL INTERRUPT
# ============================================


print("="*60)
print("PHASE 1: RUNNING GRAPH UNTIL HUMAN APPROVAL GATE")
print("="*60)


# Configuration with thread_id for state persistence
config = {"configurable": {"thread_id": "strategy-workflow-001"}}


# Initial input
initial_state = {
   "topic": "AI in Marketing",
   "content_draft": "",
   "critique": "",
   "critique_score": 0,
   "human_feedback": "",
   "revision_count": 0,
   "final_output": ""
}


# Stream events until interrupt
print("\n🏁 Starting execution...")
for event in graph.stream(initial_state, config=config, stream_mode="updates"):
   # Event contains node updates
   node_name = list(event.keys())[0]
   if node_name != "__interrupt__":
       print(f"\n[Event] Node '{node_name}' completed")


# ============================================
# 5. INSPECT THE INTERRUPT STATE
# ============================================


print("\n" + "="*60)
print("PHASE 2: GRAPH PAUSED - INSPECTING STATE")
print("="*60)


# Get current state snapshot
snapshot = graph.get_state(config)


print(f"\n📊 Current State:")
print(f"   Next nodes to execute: {snapshot.next}")
print(f"   Revision count: {snapshot.values.get('revision_count')}")
print(f"   Critique score: {snapshot.values.get('critique_score')}")


# Access the interrupt payload
if snapshot.tasks:
   interrupt_value = snapshot.tasks[0].interrupts[0].value
   print(f"\n⏸️  Interrupt Payload:")
   print(f"   Message: {interrupt_value.get('message')}")
   print(f"   Score: {interrupt_value.get('score')}/10")
   print(f"   Revisions: {interrupt_value.get('revisions_made')}")
   print(f"\n📄 Draft Preview:")
   print(f"   {interrupt_value.get('content_draft', '')[:300]}...")


# ============================================
# 6. SIMULATE HUMAN DECISION
# ============================================


print("\n" + "="*60)
print("PHASE 3: SIMULATING HUMAN DECISION")
print("="*60)


# Option 1: Approve
human_decision_approve = {
   "action": "approve",
   "feedback": "Looks great! Let's publish."
}


# Option 2: Reject with feedback
human_decision_reject = {
   "action": "reject",
   "feedback": "Add more focus on pricing strategy and competitor comparison."
}


# For this demo, let's APPROVE
print("\n👤 Human Decision: APPROVE")
selected_decision = human_decision_approve


# ============================================
# 7. RESUME EXECUTION WITH COMMAND
# ============================================


print("\n" + "="*60)
print("PHASE 4: RESUMING GRAPH WITH HUMAN INPUT")
print("="*60)


# Resume the graph by passing Command(resume=...)
# The value passed to resume becomes the return value of interrupt()
for event in graph.stream(
   Command(resume=selected_decision),
   config=config,
   stream_mode="updates"
):
   node_name = list(event.keys())[0]
   print(f"\n[Event] Node '{node_name}' completed")


# ============================================
# 8. FINAL STATE INSPECTION
# ============================================


print("\n" + "="*60)
print("PHASE 5: WORKFLOW COMPLETE - FINAL STATE")
print("="*60)


final_snapshot = graph.get_state(config)
print(f"\n✅ Final State Values:")
print(f"   Topic: {final_snapshot.values.get('topic')}")
print(f"   Revisions: {final_snapshot.values.get('revision_count')}")
print(f"   Final Score: {final_snapshot.values.get('critique_score')}/10")
print(f"   Human Feedback: {final_snapshot.values.get('human_feedback')}")
print(f"   Output Status: {'PUBLISHED' if final_snapshot.values.get('final_output') else 'NOT PUBLISHED'}")


print("\n" + "="*60)
print("🎉 WORKFLOW COMPLETE!")
print("="*60)


# ============================================
# 9. ALTERNATIVE SCENARIO: REJECTION FLOW
# ============================================


print("\n\n" + "="*60)
print("BONUS: ALTERNATIVE SCENARIO - HUMAN REJECTION")
print("="*60)


# Start a NEW thread to demonstrate rejection flow
rejection_config = {"configurable": {"thread_id": "strategy-workflow-002"}}


print("\n🏁 Starting NEW workflow...")
for event in graph.stream(initial_state, config=rejection_config, stream_mode="updates"):
   pass


print("\n👤 Human Decision: REJECT with feedback")


# Resume with rejection
for event in graph.stream(
   Command(resume=human_decision_reject),
   config=rejection_config,
   stream_mode="updates"
):
   node_name = list(event.keys())[0]
   print(f"\n[Event] Node '{node_name}' completed")


# This will loop back to planner_node, create another draft,
# go through critic again, and hit approval_gate again
# (In this demo it would need another human input to proceed)


print("\n⏸️  Graph paused again at approval gate - would need another human decision")
print("\n" + "="*60)
