"""
ITSM Agent for Bedrock AgentCore using Strands framework.
This uses the bedrock-agentcore-runtime SDK for deployment.
"""

import os
import json
import boto3
import requests
from strands import Agent, tool
from bedrock_agentcore_runtime import app, agent_function

# Initialize AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Get environment variables
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


@tool
def create_ticket(tickettype: str, description: str, impact: str, urgency: str) -> dict:
    """
    Create a new ITSM ticket.
    
    Args:
        tickettype: Type of ticket (INC for Incident, REQ for Request, CHG for Change)
        description: Description of the issue or request
        impact: Impact level (High, Medium, Low)
        urgency: Urgency level (High, Medium, Low)
    
    Returns:
        dict: Response with ticket number
    """
    try:
        url = f"{API_GATEWAY_URL}/create"
        payload = {
            "tickettype": tickettype,
            "description": description,
            "impact": impact,
            "urgency": urgency
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create ticket: {str(e)}"}


@tool
def lookup_ticket(ticketNumber: str) -> dict:
    """
    Look up an existing ITSM ticket by ticket number.
    
    Args:
        ticketNumber: The ticket number to look up (e.g., INC12345678)
    
    Returns:
        dict: Ticket details including status, description, impact, and urgency
    """
    try:
        url = f"{API_GATEWAY_URL}/lookup"
        params = {"ticketNumber": ticketNumber}
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {"error": f"Failed to lookup ticket: {str(e)}"}


@tool
def query_knowledge_base(query: str) -> dict:
    """
    Query the IT knowledge base for information about policies, procedures, and troubleshooting.
    
    Args:
        query: The question or search query
    
    Returns:
        dict: Knowledge base results with relevant information
    """
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query}
        )
        
        results = []
        for result in response.get('retrievalResults', []):
            results.append({
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0)
            })
        
        return {
            "results": results,
            "query": query
        }
    except Exception as e:
        return {"error": f"Failed to query knowledge base: {str(e)}"}


# Initialize the Strands agent with tools
agent = Agent(
    tools=[create_ticket, lookup_ticket, query_knowledge_base],
    system_prompt="""You are an IT Service Management assistant. You can help users with:
    1. Creating incident, request, and change tickets
    2. Looking up existing tickets
    3. Answering questions about IT policies and procedures
    
    When creating tickets, extract the ticket type, description, impact, and urgency from the user's request.
    Be helpful and professional in your responses."""
)


@agent_function
def handle_request(input_data: dict) -> dict:
    """
    Main handler function for AgentCore Runtime.
    
    Args:
        input_data: Request data containing the user prompt
    
    Returns:
        dict: Agent response
    """
    prompt = input_data.get('prompt', '')
    
    if not prompt:
        return {"error": "No prompt provided"}
    
    # Invoke the agent
    result = agent(prompt)
    
    return {
        "message": result.message,
        "model": "strands-agent"
    }
