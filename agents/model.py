from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent 
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from system_prompts.prompts import system_prompt
import os
from enum import Enum
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()
memory = MemorySaver()


class AgentModel(str,Enum):
    CLAUDE = "claude"
    QWEN = "qwen"


async def create_mcp_agent(model : AgentModel):

    
    if(model == AgentModel.CLAUDE):
        llm = ChatAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-sonnet-4-6"
        )
    else:
        print("created gemeini llm object...")
        llm = ChatGoogleGenerativeAI(
            google_api_key=os.getenv("GEMINI_API_KEY"),
            model="gemini-2.5-flash"
        )



    mcp_url = "http://localhost:8001"
    print(f"Connecting to MCP at: {mcp_url}/mcp", flush=True)

    client = MultiServerMCPClient(
        {
            "teams_mcp": {
                "url": f"{mcp_url}/mcp",
                "transport": "streamable_http",
            }
        }
    )

    tools = await client.get_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=memory,
        prompt=system_prompt 
    )

    return agent

async def llm_messages(agent, user_input: str, config_id: str) -> str:
    if user_input:
        config = {"configurable": {"thread_id": config_id}}
        response = await agent.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config
        )
        content = response["messages"][-1].content

        
        if isinstance(content, list):
            text_parts = [
                block["text"] for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "\n".join(text_parts)

        print(content)
        return content
    else:
        return "Hi! I am your helpful assistant."
