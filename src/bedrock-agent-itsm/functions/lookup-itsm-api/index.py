import logging
from typing import Dict, Any
from http import HTTPStatus
import json
import os
import boto3
import urllib3
from urllib.parse import urlencode, urlparse
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        action_group = event['actionGroup']
        apiPath = event['apiPath']
        httpMethod = event['httpMethod']
        message_version = event.get('messageVersion', 1)

        properties = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])

        ticketNumber = None
        for prop in properties:
            if prop.get('name') == 'ticketNumber':
                ticketNumber = prop.get('value')
                break
        
        if ticketNumber is None:
            raise KeyError('ticketNumber')

        session = boto3.Session()
        credentials = session.get_credentials().get_frozen_credentials()
        region = session.region_name or 'us-east-1'

        base_url = os.environ.get('API').rstrip('/')
        api_url = base_url + apiPath

        # Prepare query params and full URL
        query_string = urlencode({'ticketNumber': ticketNumber})
        url_with_params = api_url + '?' + query_string

        # Extract host from URL
        parsed_url = urlparse(api_url)
        host = parsed_url.netloc

        # Prepare headers without x-amz-content-sha256, SigV4Auth adds it automatically
        headers = {
            'Host': host,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Create AWSRequest and prepare it
        request = AWSRequest(method='GET', url=url_with_params, headers=headers)
        request.prepare()

        # Sign the request
        SigV4Auth(credentials, 'execute-api', region).add_auth(request)

        # Use the signed headers for the actual HTTP call
        signed_headers = dict(request.headers)

        # Make the GET request
        response = http.request(
            'GET',
            url_with_params,
            headers=signed_headers
        )

        if response.status >= 400:
            raise Exception(f"HTTP {response.status}: {response.data.decode('utf-8')}")

        api_response = json.loads(response.data.decode('utf-8'))

        ticketStatus = api_response.get('ticketStatus')
        ticketDesc = api_response.get('ticketDesc')
        ticketImpact = api_response.get('ticketImpact')
        ticketUrgency = api_response.get('ticketUrgency')
        createdAt = api_response.get('createdAt')

        response_body = {
            'application/json': {
                'body': {
                    'ticketStatus': str(ticketStatus),
                    'ticketDesc': str(ticketDesc),
                    'ticketImpact': str(ticketImpact),
                    'ticketUrgency': str(ticketUrgency),
                    'createdAt': str(createdAt)
                }
            }
        }

        action_response = {
            'actionGroup': action_group,
            'apiPath': apiPath,
            'httpMethod': httpMethod,
            'httpStatusCode': 200,
            'responseBody': response_body
        }

        response = {
            'response': action_response,
            'messageVersion': message_version
        }

        logger.info('Response: %s', response)
        return response

    except KeyError as e:
        logger.error('Missing required field: %s', str(e))
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,
            'body': f'Error: Missing required field: {str(e)}'
        }
    except Exception as e:
        logger.error('Unexpected error: %s', str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': f'Internal server error: {str(e)}'
        }