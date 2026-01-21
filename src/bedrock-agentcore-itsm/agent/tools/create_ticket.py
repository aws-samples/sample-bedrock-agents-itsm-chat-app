"""
CreateTicketTool implementation for ITSM ticket creation.

This tool provides ticket creation functionality that maintains identical
request/response formats with the Bedrock Agents implementation while
integrating with the shared API Gateway endpoints.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

import requests
from strands import Tool

logger = logging.getLogger(__name__)


class CreateTicketTool(Tool):
    """
    Tool for creating ITSM tickets through API Gateway integration.
    
    This tool ensures functional equivalence with the Bedrock Agents
    implementation by using the same API Gateway endpoints and maintaining
    identical request/response formats.
    """
    
    def __init__(self):
        """Initialize the CreateTicketTool with API configuration."""
        super().__init__()
        
        self.name = "create_ticket"
        self.description = "Create a new ITSM ticket with specified details"
        
        # API Gateway configuration
        self.api_base_url = os.getenv('API_GATEWAY_URL', '')
        self.api_key = os.getenv('API_GATEWAY_KEY', '')
        
        # Default timeout for API calls
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))
        
        logger.info("CreateTicketTool initialized")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute ticket creation with the provided parameters.
        
        Args:
            parameters: Dictionary containing ticket creation parameters:
                - tickettype: Type of ticket (INC, REQ, CHG)
                - description: Description of the issue/request
                - impact: Impact level (High, Medium, Low)
                - urgency: Urgency level (High, Medium, Low)
        
        Returns:
            Dictionary containing the API response with ticket number
        """
        try:
            # Validate required parameters
            validated_params = self._validate_parameters(parameters)
            
            # Make API call to create ticket
            response = await self._call_create_api(validated_params)
            
            logger.info(f"Ticket created successfully: {response.get('ticketNumber', 'Unknown')}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating ticket: {str(e)}")
            return {
                'statusCode': 500,
                'error': 'Ticket creation failed',
                'message': f'Failed to create ticket: {str(e)}'
            }
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize ticket creation parameters.
        
        Args:
            parameters: Raw parameters from user input
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Extract and validate tickettype
        tickettype = parameters.get('tickettype', 'INC').upper()
        if tickettype not in ['INC', 'REQ', 'CHG']:
            tickettype = 'INC'  # Default to incident
        
        # Extract and validate description
        description = parameters.get('description', '').strip()
        if not description:
            raise ValueError("Description is required for ticket creation")
        
        # Extract and validate impact
        impact = parameters.get('impact', 'Medium').title()
        if impact not in ['High', 'Medium', 'Low']:
            impact = 'Medium'  # Default to medium impact
        
        # Extract and validate urgency
        urgency = parameters.get('urgency', 'Medium').title()
        if urgency not in ['High', 'Medium', 'Low']:
            urgency = 'Medium'  # Default to medium urgency
        
        return {
            'tickettype': tickettype,
            'description': description,
            'impact': impact,
            'urgency': urgency
        }
    
    async def _call_create_api(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API call to the create-itsm Lambda function via API Gateway.
        
        Args:
            parameters: Validated ticket creation parameters
            
        Returns:
            API response dictionary
        """
        # Prepare API request
        url = f"{self.api_base_url}/create"
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key if configured
        if self.api_key:
            headers['x-api-key'] = self.api_key
        
        # Prepare request payload matching Lambda function expectations
        payload = {
            'tickettype': parameters['tickettype'],
            'description': parameters['description'],
            'impact': parameters['impact'],
            'urgency': parameters['urgency']
        }
        
        try:
            # Make synchronous HTTP request (convert to async pattern if needed)
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Handle HTTP errors
            if response.status_code != 200:
                logger.error(f"API call failed with status {response.status_code}: {response.text}")
                return {
                    'statusCode': response.status_code,
                    'error': 'API call failed',
                    'message': f'API returned status {response.status_code}'
                }
            
            # Parse and return response
            api_response = response.json()
            
            # Ensure response format matches expected structure
            return {
                'statusCode': api_response.get('statusCode', 200),
                'ticketNumber': api_response.get('ticketNumber', 'Unknown'),
                'message': api_response.get('message', 'Ticket created successfully')
            }
            
        except requests.exceptions.Timeout:
            logger.error("API call timed out")
            return {
                'statusCode': 408,
                'error': 'Request timeout',
                'message': 'API call timed out'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API")
            return {
                'statusCode': 503,
                'error': 'Service unavailable',
                'message': 'Unable to connect to ticket creation service'
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            return {
                'statusCode': 502,
                'error': 'Invalid response',
                'message': 'Received invalid response from ticket service'
            }
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            return {
                'statusCode': 500,
                'error': 'Internal error',
                'message': f'Unexpected error: {str(e)}'
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Return the tool schema for agent framework integration.
        
        Returns:
            JSON schema describing the tool's parameters and usage
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "tickettype": {
                        "type": "string",
                        "enum": ["INC", "REQ", "CHG"],
                        "description": "Type of ticket: INC (Incident), REQ (Request), CHG (Change)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the issue or request"
                    },
                    "impact": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                        "description": "Business impact level of the ticket"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                        "description": "Urgency level for resolution"
                    }
                },
                "required": ["description"]
            }
        }


# Alternative implementation using boto3 for direct Lambda invocation
class CreateTicketToolDirect(CreateTicketTool):
    """
    Alternative implementation that directly invokes the Lambda function
    instead of going through API Gateway. Useful for internal service calls.
    """
    
    def __init__(self):
        """Initialize with Lambda client instead of HTTP client."""
        super().__init__()
        
        import boto3
        self.lambda_client = boto3.client('lambda')
        self.function_name = os.getenv('CREATE_ITSM_FUNCTION_NAME', 'create-itsm')
        
        logger.info("CreateTicketToolDirect initialized with Lambda client")
    
    async def _call_create_api(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Directly invoke the create-itsm Lambda function.
        
        Args:
            parameters: Validated ticket creation parameters
            
        Returns:
            Lambda function response
        """
        try:
            # Prepare Lambda invocation payload
            payload = {
                'tickettype': parameters['tickettype'],
                'description': parameters['description'],
                'impact': parameters['impact'],
                'urgency': parameters['urgency']
            }
            
            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            # Handle Lambda errors
            if response.get('FunctionError'):
                logger.error(f"Lambda function error: {response_payload}")
                return {
                    'statusCode': 500,
                    'error': 'Lambda function error',
                    'message': 'Ticket creation function failed'
                }
            
            return response_payload
            
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {e}")
            return {
                'statusCode': 500,
                'error': 'Lambda invocation failed',
                'message': f'Failed to invoke ticket creation function: {str(e)}'
            }