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
        llm = ChatGoogleGenerativeAI(
            google_api_key=os.getenv("GEMINI_API_KEY"),
            model="gemini-1.5-pro"
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
        return response["messages"][-1].content
    else:
        return "Hi! I am your helpful assistant."
