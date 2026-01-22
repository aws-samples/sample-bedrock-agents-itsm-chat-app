import logging
import json
import boto3
import os
import hashlib
import urllib3
from http import HTTPStatus
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()

def lambda_handler(event, context):
    try:
        action_group = event['actionGroup']
        apiPath = event['apiPath']
        httpMethod = event['httpMethod']
        message_version = event.get('messageVersion', 1)

        session = boto3.Session()
        credentials = session.get_credentials().get_frozen_credentials()
        region = session.region_name or 'us-east-1'

        # Extract properties
        properties = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', [])

        tickettype = description = impact = urgency = ''
        for prop in properties:
            if prop.get('name') == 'tickettype':
                tickettype = prop.get('value')
            elif prop.get('name') == 'description':
                description = prop.get('value')
            elif prop.get('name') == 'impact':
                impact = prop.get('value')
            elif prop.get('name') == 'urgency':
                urgency = prop.get('value')

        ticketdata = {
            'tickettype': tickettype,
            'description': description,
            'impact': impact,
            'urgency': urgency
        }

        api_url = os.environ.get('API').rstrip('/') + '/' + apiPath.lstrip('/')

        body_bytes = json.dumps(ticketdata).encode('utf-8')

        # Prepare headers (Host is required for SigV4)
        host = api_url.split('//')[1].split('/')[0]
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Host': host,
            'x-amz-content-sha256': hashlib.sha256(body_bytes).hexdigest()
        }

        # Create AWSRequest and sign it
        request = AWSRequest(method='POST', url=api_url, data=body_bytes, headers=headers)
        SigV4Auth(credentials, 'execute-api', region).add_auth(request)
        signed_headers = dict(request.headers)

        # Send the request with urllib3
        response = http.request(
            'POST',
            api_url,
            body=body_bytes,
            headers=signed_headers
        )

        if response.status >= 400:
            raise Exception(f"HTTP {response.status}: {response.data.decode('utf-8')}")

        response_json = json.loads(response.data.decode('utf-8'))
        ticket_number = response_json.get('ticketNumber')

        response_body = {
            'application/json': {
                'ticketNumber': str(ticket_number)
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
            'body': f'Error: {str(e)}'
        }
    except Exception as e:
        logger.error('Unexpected error: %s', str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': f'Internal server error: {str(e)}'
        }