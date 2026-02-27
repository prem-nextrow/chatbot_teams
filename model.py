from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
import os
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent

load_dotenv()
memory=MemorySaver()

async def chat_llm():


    llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_END_POINT"),   
    api_version=os.getenv("AZURE_VERSION"),       
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    api_key=os.getenv("AZURE_API_KEY"),           
    temperature=0.7
)
    agent=create_agent(
        model=llm,
        checkpointer=memory,
        system_prompt="you are the help full assistance to clear all the doubt and task given to you"
    )
    return agent



async def llm_messages(agent,user_input,config_id):
    print("\n" + "="*60)

    if(user_input):
        config={"configurable":{"thread_id":config_id}}
        response=agent.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        return response["messages"][-1].content
    else:
        return "Hii I am the helpfull Assistant"
