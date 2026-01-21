"""
ITSM Agent for Bedrock AgentCore using Strands framework.
This uses the bedrock-agentcore SDK for deployment.
"""

import os
import json
import boto3
import requests
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Get environment variables
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize AWS clients with region (lazy initialization to avoid startup errors)
_bedrock_client = None

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
    return _bedrock_client


@app.entrypoint
def handle_request(input_data: dict) -> dict:
    """
    Main entrypoint for AgentCore Runtime.
    
    Args:
        input_data: Request data containing the user prompt
    
    Returns:
        dict: Agent response
    """
    prompt = input_data.get('prompt', '')
    
    if not prompt:
        return {"error": "No prompt provided"}
    
    # Simple intent detection
    prompt_lower = prompt.lower()
    
    # Check for ticket creation
    if any(word in prompt_lower for word in ['create', 'new', 'open', 'ticket', 'incident', 'issue']):
        # Extract basic info and create ticket
        ticket_type = 'INC' if 'incident' in prompt_lower else 'REQ'
        impact = 'High' if 'high' in prompt_lower or 'critical' in prompt_lower else 'Medium'
        urgency = 'High' if 'urgent' in prompt_lower or 'asap' in prompt_lower else 'Medium'
        
        result = create_ticket(ticket_type, prompt, impact, urgency)
        
        if 'error' in result:
            return {"message": f"I encountered an error: {result['error']}"}
        else:
            return {"message": f"I've created ticket {result.get('ticketNumber', 'Unknown')} for you."}
    
    # Check for ticket lookup
    elif any(word in prompt_lower for word in ['lookup', 'find', 'check', 'status']):
        # Try to extract ticket number
        import re
        ticket_match = re.search(r'(INC|REQ|CHG)\d{8}', prompt.upper())
        
        if ticket_match:
            ticket_number = ticket_match.group(0)
            result = lookup_ticket(ticket_number)
            
            if 'error' in result:
                return {"message": f"I encountered an error: {result['error']}"}
            else:
                status = result.get('ticketStatus', 'Unknown')
                return {"message": f"Ticket {ticket_number} status: {status}"}
        else:
            return {"message": "Please provide a ticket number (e.g., INC12345678)"}
    
    # Check for knowledge base query
    elif any(word in prompt_lower for word in ['how', 'what', 'policy', 'procedure', 'help']):
        result = query_knowledge_base(prompt)
        
        if 'error' in result:
            return {"message": f"I encountered an error: {result['error']}"}
        else:
            results = result.get('results', [])
            if results:
                answer = results[0].get('content', 'No information found')
                return {"message": answer}
            else:
                return {"message": "I couldn't find any relevant information in the knowledge base."}
    
    # Default response
    else:
        return {
            "message": "I can help you with:\n1. Creating tickets (incidents, requests)\n2. Looking up ticket status\n3. Answering questions about IT policies and procedures"
        }


def create_ticket(tickettype: str, description: str, impact: str, urgency: str) -> dict:
    """Create a new ITSM ticket."""
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


def lookup_ticket(ticketNumber: str) -> dict:
    """Look up an existing ITSM ticket."""
    try:
        url = f"{API_GATEWAY_URL}/lookup"
        params = {"ticketNumber": ticketNumber}
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {"error": f"Failed to lookup ticket: {str(e)}"}


def query_knowledge_base(query: str) -> dict:
    """Query the IT knowledge base."""
    try:
        client = get_bedrock_client()
        response = client.retrieve(
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
