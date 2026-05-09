from langchain_openai import ChatOpenAI
from .tools import (
    scrape_product,
    get_product,
    get_price_history,
    search_products,
    vector_search
)
from .agent_prompt import AGENT_SYSTEM_PROMPT
import os
import json


def create_agent():
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )
    
    tools = [
        scrape_product,
        get_product,
        get_price_history,
        search_products,
        vector_search
    ]
    
    tool_map = {tool.name: tool for tool in tools}
    llm_with_tools = llm.bind_tools(tools)
    
    class AgentExecutor:
        def invoke(self, inputs, max_iterations=5):
            user_input = inputs.get("input", "")
            messages = [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
            
            for iteration in range(max_iterations):
                response = llm_with_tools.invoke(messages)
                messages.append(response)
                
                if not hasattr(response, "tool_calls") or not response.tool_calls:
                    return {"output": response.content}
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("args", {})
                    
                    if tool_name in tool_map:
                        try:
                            result = tool_map[tool_name].invoke(tool_args)
                            
                            if isinstance(result, dict):
                                if "products" in result and result["products"]:
                                    products_info = []
                                    for p in result["products"]:
                                        info = f"ASIN: {p.get('asin')}, Title: {p.get('title')}, Price: {p.get('price_display', 'N/A')}, Location: {p.get('geo_location')}, Rating: {p.get('rating', 'N/A')}"
                                        products_info.append(info)
                                    tool_result = f"Found {len(result['products'])} products:\n" + "\n".join(products_info)
                                elif "contexts" in result and result["contexts"]:
                                    contexts = "\n\n".join([f"Product {i+1}:\n{ctx}" for i, ctx in enumerate(result["contexts"])])
                                    tool_result = f"Found {len(result['contexts'])} matching products:\n\n{contexts}"
                                else:
                                    tool_result = json.dumps(result, indent=2, default=str)
                            elif isinstance(result, list):
                                if result and isinstance(result[0], dict):
                                    items_info = []
                                    for item in result:
                                        if isinstance(item, dict):
                                            info_parts = [f"{k}: {v}" for k, v in item.items() if v]
                                            items_info.append(", ".join(info_parts))
                                    tool_result = "\n".join(items_info) if items_info else json.dumps(result, indent=2, default=str)
                                else:
                                    tool_result = json.dumps(result, indent=2, default=str)
                            else:
                                tool_result = str(result)
                        except Exception as e:
                            import traceback
                            tool_result = f"Error executing {tool_name}: {str(e)}\n{traceback.format_exc()}"
                    else:
                        tool_result = f"Tool {tool_name} not found"
                    
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call.get("id", "")
                    })
            
            final_response = llm_with_tools.invoke(messages)
            return {"output": final_response.content}
    
    return AgentExecutor()