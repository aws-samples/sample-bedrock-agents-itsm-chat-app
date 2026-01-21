"""
Main Strands agent implementation for ITSM system using Bedrock AgentCore.

This module implements the core agent orchestration logic that handles
user requests for IT Service Management operations including ticket creation,
ticket lookup, and knowledge base queries.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

import boto3
from strands import Agent, Tool

from .tools.create_ticket import CreateTicketTool
from .tools.lookup_ticket import LookupTicketTool
from .tools.knowledge_base import KnowledgeBaseTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ITSMAgent(Agent):
    """
    Main ITSM Agent implementation using Strands framework.
    
    This agent provides IT Service Management capabilities including:
    - Creating support tickets
    - Looking up existing tickets
    - Querying knowledge base for solutions
    
    The agent maintains functional equivalence with the Bedrock Agents
    implementation while providing greater customization flexibility.
    """
    
    def __init__(self):
        """Initialize the ITSM agent with required tools and configuration."""
        super().__init__()
        
        # Initialize tools
        self.tools = [
            CreateTicketTool(),
            LookupTicketTool(), 
            KnowledgeBaseTool()
        ]
        
        # Agent configuration
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        self.max_iterations = int(os.getenv('MAX_ITERATIONS', '10'))
        
        # Initialize Bedrock client
        self.bedrock_client = boto3.client('bedrock-runtime')
        
        logger.info(f"ITSM Agent initialized with {len(self.tools)} tools")
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming user requests and orchestrate tool usage.
        
        Args:
            request: User request containing message and context
            
        Returns:
            Response dictionary with agent's reply and any tool results
        """
        try:
            user_message = request.get('message', '')
            session_id = request.get('sessionId', 'default')
            
            logger.info(f"Processing request for session {session_id}: {user_message[:100]}...")
            
            # Analyze user intent and determine appropriate tool usage
            intent = await self._analyze_intent(user_message)
            
            # Execute appropriate tool based on intent
            if intent['action'] == 'create_ticket':
                tool_result = await self._execute_create_ticket(intent['parameters'])
            elif intent['action'] == 'lookup_ticket':
                tool_result = await self._execute_lookup_ticket(intent['parameters'])
            elif intent['action'] == 'knowledge_query':
                tool_result = await self._execute_knowledge_query(intent['parameters'])
            else:
                # General conversation or unclear intent
                tool_result = await self._handle_general_conversation(user_message)
            
            # Format response
            response = {
                'statusCode': 200,
                'sessionId': session_id,
                'message': tool_result.get('message', ''),
                'toolResults': tool_result.get('results', [])
            }
            
            logger.info(f"Request processed successfully for session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                'statusCode': 500,
                'error': 'Internal server error',
                'message': 'I encountered an error processing your request. Please try again.'
            }
    
    async def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        Analyze user message to determine intent and extract parameters.
        
        Args:
            message: User's input message
            
        Returns:
            Dictionary containing action and extracted parameters
        """
        message_lower = message.lower()
        
        # Simple intent classification based on keywords
        if any(keyword in message_lower for keyword in ['create', 'new', 'ticket', 'issue', 'problem']):
            return {
                'action': 'create_ticket',
                'parameters': await self._extract_ticket_parameters(message)
            }
        elif any(keyword in message_lower for keyword in ['lookup', 'find', 'search', 'status', 'check']):
            return {
                'action': 'lookup_ticket', 
                'parameters': await self._extract_lookup_parameters(message)
            }
        elif any(keyword in message_lower for keyword in ['help', 'how', 'what', 'knowledge', 'documentation']):
            return {
                'action': 'knowledge_query',
                'parameters': {'query': message}
            }
        else:
            return {
                'action': 'general_conversation',
                'parameters': {'message': message}
            }
    
    async def _extract_ticket_parameters(self, message: str) -> Dict[str, Any]:
        """Extract ticket creation parameters from user message."""
        # Use Bedrock to extract structured parameters
        prompt = f"""
        Extract ticket creation parameters from this message: "{message}"
        
        Return a JSON object with these fields:
        - tickettype: "INC" for incident, "REQ" for request, "CHG" for change
        - description: Brief description of the issue
        - impact: "High", "Medium", or "Low"
        - urgency: "High", "Medium", or "Low"
        
        If any field cannot be determined, use reasonable defaults.
        """
        
        try:
            response = await self._call_bedrock(prompt)
            return json.loads(response)
        except Exception as e:
            logger.warning(f"Failed to extract parameters, using defaults: {e}")
            return {
                'tickettype': 'INC',
                'description': message,
                'impact': 'Medium',
                'urgency': 'Medium'
            }
    
    async def _extract_lookup_parameters(self, message: str) -> Dict[str, Any]:
        """Extract ticket lookup parameters from user message."""
        # Simple extraction of ticket number patterns
        import re
        ticket_pattern = r'(INC|REQ|CHG)\d{8}'
        match = re.search(ticket_pattern, message.upper())
        
        if match:
            return {'ticketNumber': match.group(0)}
        else:
            return {'query': message}
    
    async def _execute_create_ticket(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ticket creation using CreateTicketTool."""
        create_tool = next(tool for tool in self.tools if isinstance(tool, CreateTicketTool))
        result = await create_tool.execute(parameters)
        
        return {
            'message': f"I've created your ticket: {result.get('ticketNumber', 'Unknown')}",
            'results': [result]
        }
    
    async def _execute_lookup_ticket(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ticket lookup using LookupTicketTool."""
        lookup_tool = next(tool for tool in self.tools if isinstance(tool, LookupTicketTool))
        result = await lookup_tool.execute(parameters)
        
        if result.get('statusCode') == 200 and 'ticketStatus' in result:
            message = f"Ticket Status: {result['ticketStatus']}"
            if result.get('ticketDesc'):
                message += f"\nDescription: {result['ticketDesc']}"
            if result.get('ticketImpact'):
                message += f"\nImpact: {result['ticketImpact']}"
            if result.get('ticketUrgency'):
                message += f"\nUrgency: {result['ticketUrgency']}"
        else:
            message = result.get('ticketStatus', 'Unable to retrieve ticket information')
        
        return {
            'message': message,
            'results': [result]
        }
    
    async def _execute_knowledge_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute knowledge base query using KnowledgeBaseTool."""
        kb_tool = next(tool for tool in self.tools if isinstance(tool, KnowledgeBaseTool))
        result = await kb_tool.execute(parameters)
        
        return {
            'message': result.get('answer', 'I found some information that might help.'),
            'results': [result]
        }
    
    async def _handle_general_conversation(self, message: str) -> Dict[str, Any]:
        """Handle general conversation that doesn't require specific tools."""
        prompt = f"""
        You are an IT Service Management assistant. The user said: "{message}"
        
        Provide a helpful response. If they need to create a ticket, lookup a ticket, 
        or need technical help, guide them on how to do so.
        
        Keep your response concise and professional.
        """
        
        response = await self._call_bedrock(prompt)
        
        return {
            'message': response,
            'results': []
        }
    
    async def _call_bedrock(self, prompt: str) -> str:
        """Make a call to Bedrock for text generation."""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Error calling Bedrock: {e}")
            return "I'm having trouble processing that request right now."


# Entry point for AgentCore Runtime
def lambda_handler(event, context):
    """
    Lambda handler for AgentCore Runtime integration.
    
    This function serves as the entry point when the agent is deployed
    as a container in the AgentCore Runtime environment.
    """
    agent = ITSMAgent()
    
    # Extract request from event
    request = {
        'message': event.get('inputText', ''),
        'sessionId': event.get('sessionId', 'default')
    }
    
    # Process request asynchronously
    import asyncio
    response = asyncio.run(agent.process_request(request))
    
    return response