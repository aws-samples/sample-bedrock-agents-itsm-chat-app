"""
ITSM Agent for Bedrock AgentCore using Strands framework.
"""

import os
import json
import boto3
import requests
import logging
from strands import Agent, tool
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the AgentCore app
app = BedrockAgentCoreApp()

# Get environment variables
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
MEMORY_ID = os.environ.get('MEMORY_ID')  # Required: Memory ID created via CLI

if MEMORY_ID:
    logger.info(f"Memory enabled with ID: {MEMORY_ID}")
else:
    logger.warning("No MEMORY_ID provided - agent will run in stateless mode")


@tool
def create_ticket(tickettype: str, description: str, impact: str, urgency: str) -> dict:
    """
    Create a new IT service management ticket.
    
    Args:
        tickettype: Type of ticket - INC for Incident, REQ for Request, CHG for Change
        description: Detailed description of the issue or request
        impact: Impact level - High, Medium, or Low
        urgency: Urgency level - High, Medium, or Low
    
    Returns:
        Dictionary with ticket number and status
    """
    try:
        url = f"{API_GATEWAY_URL}/create"
        payload = {
            "tickettype": tickettype,
            "description": description,
            "impact": impact,
            "urgency": urgency
        }
        
        # Sign request with AWS SigV4
        session = boto3.Session()
        credentials = session.get_credentials()
        
        request = AWSRequest(
            method='POST',
            url=url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'execute-api', AWS_REGION).add_auth(request)
        
        response = requests.post(
            url,
            data=request.body,
            headers=dict(request.headers),
            timeout=30
        )
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {"error": f"Failed to create ticket: {str(e)}"}


@tool
def lookup_ticket(ticketNumber: str) -> dict:
    """
    Look up an existing IT service management ticket by ticket number.
    
    Args:
        ticketNumber: The ticket number to look up (e.g., INC12345678, REQ12345678, CHG12345678)
    
    Returns:
        Dictionary with ticket status and details
    """
    try:
        url = f"{API_GATEWAY_URL}/lookup?ticketNumber={ticketNumber}"
        
        # Sign request with AWS SigV4
        session = boto3.Session()
        credentials = session.get_credentials()
        
        request = AWSRequest(
            method='GET',
            url=url,
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'execute-api', AWS_REGION).add_auth(request)
        
        response = requests.get(
            url,
            headers=dict(request.headers),
            timeout=30
        )
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {"error": f"Failed to lookup ticket: {str(e)}"}


@tool
def query_knowledge_base(query: str) -> dict:
    """
    Search the IT knowledge base for information about policies, procedures, and troubleshooting.
    
    Args:
        query: The question or search query for the knowledge base
    
    Returns:
        Dictionary with answer and source information
    """
    logger.info(f"KB Tool called with query: {query}")
    try:
        client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
        response = client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query}
        )
        
        logger.info(f"KB returned {len(response.get('retrievalResults', []))} results")
        
        results = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            score = result.get('score', 0)
            logger.info(f"KB result score: {score}")
            if content:
                results.append({
                    'content': content,
                    'score': score
                })
        
        if results:
            top_results = results[:3]
            logger.info(f"Returning {len(top_results)} results to agent")
            return {
                "found": True,
                "results": [r['content'] for r in top_results],
                "message": f"Found {len(results)} relevant document(s)."
            }
        else:
            logger.warning("No KB results found")
            return {
                "found": False,
                "message": "No relevant information found in the knowledge base."
            }
    except Exception as e:
        logger.error(f"KB query failed: {str(e)}")
        return {"error": f"Failed to query knowledge base: {str(e)}"}


# Initialize Strands agent with tools (without session manager - will be created per request)
def create_agent(session_manager=None):
    """Create a Strands agent with optional session manager for memory."""
    return Agent(
        tools=[create_ticket, lookup_ticket, query_knowledge_base],
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        session_manager=session_manager,
        system_prompt="""You are an IT Service Management assistant. You help users with:
1. Creating IT tickets (incidents for problems, requests for services, changes for modifications)
2. Looking up existing ticket status
3. Answering questions about IT policies, procedures, and troubleshooting

IMPORTANT: For ANY question about policies, procedures, or IT information, you MUST use the query_knowledge_base tool. 
Do NOT answer questions from your own knowledge - always search the knowledge base first.

When creating tickets:
- You MUST collect ALL required information before calling the create_ticket tool:
  * tickettype: Must be INC (incident), REQ (request), or CHG (change)
  * description: Detailed description of the issue or request
  * impact: Must be High, Medium, or Low
  * urgency: Must be High, Medium, or Low
- If ANY required field is missing, ask the user for it - do NOT proceed without all information
- Continue prompting until you have collected all four required fields
- Determine appropriate ticket type based on the user's needs:
  * INC for incidents/problems/issues
  * REQ for service requests/access requests
  * CHG for changes/modifications
- Help determine impact and urgency by asking clarifying questions if needed
- Only call create_ticket once you have all four required parameters

When answering questions:
- ALWAYS call query_knowledge_base tool for any question
- Extract only the relevant parts from the KB results
- Provide clear, concise answers based on the KB content
- If KB has no information, say so and offer to create a ticket

Be helpful, professional, and conversational."""
    )


@app.entrypoint
def handle_request(input_data: dict) -> dict:
    """
    Main entrypoint for AgentCore Runtime with memory support.
    
    Args:
        input_data: Request data containing the user prompt and optional session_id
    
    Returns:
        dict: Agent response
    """
    prompt = input_data.get('prompt', '')
    session_id = input_data.get('session_id')  # Optional session ID for memory
    actor_id = input_data.get('actor_id', 'default_user')  # Optional actor ID
    
    if not prompt:
        return {"error": "No prompt provided"}
    
    logger.info(f"Received prompt: {prompt}")
    if session_id:
        logger.info(f"Session ID: {session_id}, Actor ID: {actor_id}")
    
    try:
        # Create agent with or without memory based on session_id
        if session_id and MEMORY_ID:
            # Configure memory for this session
            agentcore_memory_config = AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id=actor_id
            )
            
            # Create session manager
            session_manager = AgentCoreMemorySessionManager(
                agentcore_memory_config=agentcore_memory_config,
                region_name=AWS_REGION
            )
            
            # Create agent with memory
            agent = create_agent(session_manager=session_manager)
            logger.info("Agent created with memory enabled")
        else:
            # Create agent without memory (stateless)
            agent = create_agent()
            logger.info("Agent created without memory (stateless)")
        
        # Invoke the Strands agent
        result = agent(prompt)
        
        logger.info("Agent response received")
        
        response = {
            "message": result.message
        }
        
        # Include session_id in response if provided
        if session_id:
            response["session_id"] = session_id
        
        return response
    except Exception as e:
        logger.error(f"Agent invocation failed: {str(e)}")
        return {"error": f"Failed to process request: {str(e)}"}
