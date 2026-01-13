"""
LookupTicketTool implementation for ITSM ticket lookup.

This tool provides ticket lookup functionality that maintains identical
request/response formats with the Bedrock Agents implementation while
integrating with the shared API Gateway endpoints.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

import requests
from strands_agents import Tool

logger = logging.getLogger(__name__)


class LookupTicketTool(Tool):
    """
    Tool for looking up ITSM tickets through API Gateway integration.
    
    This tool ensures functional equivalence with the Bedrock Agents
    implementation by using the same API Gateway endpoints and maintaining
    identical request/response formats.
    """
    
    def __init__(self):
        """Initialize the LookupTicketTool with API configuration."""
        super().__init__()
        
        self.name = "lookup_ticket"
        self.description = "Look up an existing ITSM ticket by ticket number"
        
        # API Gateway configuration
        self.api_base_url = os.getenv('API_GATEWAY_URL', '')
        self.api_key = os.getenv('API_GATEWAY_KEY', '')
        
        # Default timeout for API calls
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))
        
        logger.info("LookupTicketTool initialized")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute ticket lookup with the provided parameters.
        
        Args:
            parameters: Dictionary containing lookup parameters:
                - ticketNumber: The ticket number to look up (e.g., INC12345678)
                - query: Alternative search query if ticket number not provided
        
        Returns:
            Dictionary containing the ticket information or error message
        """
        try:
            # Validate and extract ticket number
            ticket_number = self._extract_ticket_number(parameters)
            
            if not ticket_number:
                return {
                    'statusCode': 400,
                    'error': 'Invalid parameters',
                    'ticketStatus': 'Please provide a valid ticket number (e.g., INC12345678)'
                }
            
            # Make API call to lookup ticket
            response = await self._call_lookup_api(ticket_number)
            
            logger.info(f"Ticket lookup completed for: {ticket_number}")
            return response
            
        except Exception as e:
            logger.error(f"Error looking up ticket: {str(e)}")
            return {
                'statusCode': 500,
                'error': 'Ticket lookup failed',
                'ticketStatus': f'Failed to lookup ticket: {str(e)}'
            }
    
    def _extract_ticket_number(self, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Extract and validate ticket number from parameters.
        
        Args:
            parameters: Input parameters containing ticket number or query
            
        Returns:
            Validated ticket number or None if not found/invalid
        """
        # Direct ticket number parameter
        ticket_number = parameters.get('ticketNumber', '').strip()
        
        if ticket_number:
            # Validate ticket number format
            if self._is_valid_ticket_number(ticket_number):
                return ticket_number.upper()
        
        # Try to extract from query parameter
        query = parameters.get('query', '').strip()
        if query:
            # Use regex to find ticket number pattern in query
            import re
            ticket_pattern = r'(INC|REQ|CHG)\d{8}'
            match = re.search(ticket_pattern, query.upper())
            if match:
                return match.group(0)
        
        return None
    
    def _is_valid_ticket_number(self, ticket_number: str) -> bool:
        """
        Validate ticket number format.
        
        Args:
            ticket_number: Ticket number to validate
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        # Expected format: INC/REQ/CHG followed by 8 digits
        pattern = r'^(INC|REQ|CHG)\d{8}$'
        return bool(re.match(pattern, ticket_number.upper()))
    
    async def _call_lookup_api(self, ticket_number: str) -> Dict[str, Any]:
        """
        Make API call to the lookup-itsm Lambda function via API Gateway.
        
        Args:
            ticket_number: Validated ticket number to lookup
            
        Returns:
            API response dictionary with ticket information
        """
        # Prepare API request
        url = f"{self.api_base_url}/lookup"
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key if configured
        if self.api_key:
            headers['x-api-key'] = self.api_key
        
        # Prepare request payload matching Lambda function expectations
        payload = {
            'ticketNumber': ticket_number
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
                    'ticketStatus': f'API returned status {response.status_code}'
                }
            
            # Parse and return response
            api_response = response.json()
            
            # Ensure response format matches expected structure from Lambda function
            return {
                'statusCode': api_response.get('statusCode', 200),
                'ticketStatus': api_response.get('ticketStatus', 'Unknown status'),
                'ticketDesc': api_response.get('ticketDesc'),
                'ticketImpact': api_response.get('ticketImpact'),
                'ticketUrgency': api_response.get('ticketUrgency'),
                'createdAt': api_response.get('createdAt')
            }
            
        except requests.exceptions.Timeout:
            logger.error("API call timed out")
            return {
                'statusCode': 408,
                'error': 'Request timeout',
                'ticketStatus': 'API call timed out'
            }
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API")
            return {
                'statusCode': 503,
                'error': 'Service unavailable',
                'ticketStatus': 'Unable to connect to ticket lookup service'
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            return {
                'statusCode': 502,
                'error': 'Invalid response',
                'ticketStatus': 'Received invalid response from ticket service'
            }
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            return {
                'statusCode': 500,
                'error': 'Internal error',
                'ticketStatus': f'Unexpected error: {str(e)}'
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
                    "ticketNumber": {
                        "type": "string",
                        "pattern": "^(INC|REQ|CHG)\\d{8}$",
                        "description": "Ticket number to lookup (e.g., INC12345678, REQ87654321)"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query containing ticket number or description"
                    }
                },
                "anyOf": [
                    {"required": ["ticketNumber"]},
                    {"required": ["query"]}
                ]
            }
        }


# Alternative implementation using boto3 for direct Lambda invocation
class LookupTicketToolDirect(LookupTicketTool):
    """
    Alternative implementation that directly invokes the Lambda function
    instead of going through API Gateway. Useful for internal service calls.
    """
    
    def __init__(self):
        """Initialize with Lambda client instead of HTTP client."""
        super().__init__()
        
        import boto3
        self.lambda_client = boto3.client('lambda')
        self.function_name = os.getenv('LOOKUP_ITSM_FUNCTION_NAME', 'lookup-itsm')
        
        logger.info("LookupTicketToolDirect initialized with Lambda client")
    
    async def _call_lookup_api(self, ticket_number: str) -> Dict[str, Any]:
        """
        Directly invoke the lookup-itsm Lambda function.
        
        Args:
            ticket_number: Validated ticket number to lookup
            
        Returns:
            Lambda function response
        """
        try:
            # Prepare Lambda invocation payload
            payload = {
                'ticketNumber': ticket_number
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
                    'ticketStatus': 'Ticket lookup function failed'
                }
            
            return response_payload
            
        except Exception as e:
            logger.error(f"Error invoking Lambda function: {e}")
            return {
                'statusCode': 500,
                'error': 'Lambda invocation failed',
                'ticketStatus': f'Failed to invoke ticket lookup function: {str(e)}'
            }


# Utility class for advanced ticket search functionality
class TicketSearchHelper:
    """
    Helper class for advanced ticket search and filtering capabilities.
    
    This class can be extended to provide more sophisticated search
    functionality beyond simple ticket number lookup.
    """
    
    def __init__(self):
        """Initialize search helper with DynamoDB client."""
        import boto3
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'itsm-tickets')
        self.table = self.dynamodb.Table(self.table_name)
    
    async def search_by_description(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search tickets by description content.
        
        Args:
            search_term: Term to search for in ticket descriptions
            
        Returns:
            List of matching tickets
        """
        try:
            # Note: This would require a GSI on description field for efficient searching
            # For now, this is a placeholder for future enhancement
            response = self.table.scan(
                FilterExpression='contains(ticketDesc, :term)',
                ExpressionAttributeValues={':term': search_term}
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error searching tickets by description: {e}")
            return []
    
    async def search_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Search tickets by status.
        
        Args:
            status: Status to filter by (Pending, In Progress, Resolved)
            
        Returns:
            List of tickets with matching status
        """
        try:
            # Note: This would require a GSI on status field for efficient searching
            response = self.table.scan(
                FilterExpression='ticketStatus = :status',
                ExpressionAttributeValues={':status': status}
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error searching tickets by status: {e}")
            return []