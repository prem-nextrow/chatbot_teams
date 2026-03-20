from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
import os
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from services.koru_mcp_server import mcp

load_dotenv()
memory = MemorySaver()


async def chat_llm():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.7
    )
    agent = create_agent(
        model=llm,
        checkpointer=memory,
        system_prompt="""You are a helpful AI assistant specializing in KORU marketing analytics reports.

IMPORTANT: When users greet you or ask general questions, ALWAYS mention that you can help analyze KORU marketing audit reports and suggest they ask to "list reports" to see available reports.

When users ask to analyze a report, provide detailed insights about the marketing tags, vendors, and analytics implementation.

Available commands:
- "list reports" - Shows all available KORU reports
- "analyze [report_name]" - Analyzes a specific report
- Send a report name directly (e.g., "hyatt-koru-report.xlsx") - Analyzes that report

Be professional, clear, and data-driven in your responses. Always guide users toward the KORU report analysis functionality."""
    )
    return agent


async def llm_messages(agent, user_input, config_id):
    print("\n" + "="*60)
    print(f"User input: '{user_input}'")
    
    if not user_input:
        # Empty message - show reports list
        result = await mcp.call_tool("list_reports", {})
        reports = result.structured_content.get("result", "No reports found") if hasattr(result, 'structured_content') else str(result)
        if reports and reports != "No reports found":
            return f"""Hi there! 👋 Welcome!

I'm here to help you analyze KORU marketing audit reports.

📊 Available Reports:
{reports}

To analyze a report, just send me the report name (e.g., "hyatt-koru-report.xlsx" or just "hyatt")."""
        else:
            return "Hi there! 👋 Welcome! I'm ready to help, but no reports are currently available."
    
    user_lower = user_input.lower().strip()
    
    # Handle greetings - list reports using MCP tool
    # Check for common greetings
    greeting_words = ["hi", "hello", "hey", "start", "greetings", "good morning", "good afternoon", "good evening"]
    if any(greeting in user_lower for greeting in greeting_words) and len(user_input.split()) <= 3:
        result = await mcp.call_tool("list_reports", {})
        reports = result.structured_content.get("result", "No reports found") if hasattr(result, 'structured_content') else str(result)
        if reports and reports != "No reports found":
            return f"""Hi there! 👋 Welcome!

I'm here to help you analyze KORU marketing audit reports.

📊 Available Reports:
{reports}

To analyze a report, just send me the report name (e.g., "hyatt-koru-report.xlsx" or just "hyatt")."""
        else:
            return "Hi there! 👋 Welcome! I'm ready to help, but no reports are currently available."
    
    # Handle list reports request using MCP tool
    if "list" in user_lower and "report" in user_lower:
        result = await mcp.call_tool("list_reports", {})
        reports = result.structured_content.get("result", "No reports found") if hasattr(result, 'structured_content') else str(result)
        if reports and reports != "No reports found":
            return f"📊 Available KORU Reports:\n{reports}"
        else:
            return "No reports found."
    
    # Handle analyze request using MCP tool
    if "analyze" in user_lower or "analyse" in user_lower:
        words = user_input.split()
        report_name = words[-1]
        
        result = await mcp.call_tool("analyze_report", {"report_name": report_name})
        insights = result.structured_content.get("result", str(result)) if hasattr(result, 'structured_content') else str(result)
        return insights
    
    # Check if user is sending a report name directly using MCP tool
    if user_input.endswith(".xlsx") or any(word in user_lower for word in ["-koru-", "report"]):
        report_name = user_input.strip()
        result = await mcp.call_tool("analyze_report", {"report_name": report_name})
        insights = result.structured_content.get("result", str(result)) if hasattr(result, 'structured_content') else str(result)
        return insights
    
    # Default: use agent for general conversation
    config = {"configurable": {"thread_id": config_id}}
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    return response["messages"][-1].content
