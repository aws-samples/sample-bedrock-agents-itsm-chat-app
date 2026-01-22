# Bedrock AgentCore ITSM Implementation

This directory contains the Bedrock AgentCore implementation of the ITSM chat solution. This approach uses a container-based runtime designed for production deployments that require enterprise-grade customization, control, and integration with frameworks like LangChain, LangGraph, and Strands.

## Overview

The AgentCore implementation provides:

* **Container-Based Deployment**: Modern containerized deployment using Amazon Bedrock AgentCore
* **Custom Agent Logic**: Complete control using Python and the Strands framework
* **Framework Flexibility**: Use any Python AI framework (LangChain, LangGraph, Strands, etc.)
* **Advanced Debugging**: Direct access to agent code for debugging and monitoring
* **Enterprise-Grade**: Built on AgentCore, designed for production workloads with enterprise customization and control

## Architecture

![Architecture Diagram](../../docs/bedrock-agentcore-lab.png)


## Prerequisites

Before deploying the AgentCore implementation, ensure you have:

### Required Tools
* **AWS CLI v2** - For interacting with AWS services
* **Docker** - For building container images  
* **SAM CLI** - For deploying serverless applications
* **Python 3.11+** - For running validation scripts
* **Node.js 18+** - For building Lambda functions
* **npm** - Node package manager (included with Node.js)

### Installation Commands

Install AWS CLI (macOS):
```bash
brew install awscli
```

Install Docker (macOS):
```bash
brew install docker
```

Install SAM CLI:
```bash
brew install aws-sam-cli
```

Install Node.js (includes npm):
```bash
brew install node
```

Verify installations:
```bash
aws --version
docker --version
sam --version
python3 --version
node --version
npm --version
```

### AWS Configuration

Configure AWS credentials:
```bash
aws configure
```

Or use a specific profile:
```bash
aws configure --profile myprofile
```

Set the profile as default for all commands (optional):
```bash
export AWS_PROFILE=myprofile
```

Verify your identity:
```bash
aws sts get-caller-identity
```

Or verify identity for a specific profile:
```bash
aws sts get-caller-identity --profile myprofile
```

## Deployment Process

The AgentCore deployment demonstrates container-based AI agent deployment. You'll execute each step to understand the deployment process.

### Step 1: Environment Validation

First, validate that all required AWS services are available in your target region.

Set your target region:
```bash
export AWS_REGION=us-east-1
```

If using a specific profile, set it now (optional):
```bash
export AWS_PROFILE=myprofile
```

Check Bedrock Agent availability:
```bash
aws bedrock-agent list-knowledge-bases --region $AWS_REGION --max-results 1
```

Check other required services:
```bash
aws dynamodb list-tables --region $AWS_REGION --limit 1
aws s3 ls
aws opensearch list-domain-names --region $AWS_REGION
aws apigateway get-rest-apis --region $AWS_REGION --limit 1
aws lambda list-functions --region $AWS_REGION --max-items 1
aws ecr describe-repositories --region $AWS_REGION --max-results 1
```

**Expected Results:**
* Each command should return successfully (not "service not available" errors)
* You may see "AccessDenied" errors - this is normal if you don't have data yet
* "UnauthorizedOperation" errors indicate the service is available but you need permissions

### Step 2: Container Preparation

Navigate to the AgentCore directory:
```bash
cd src/bedrock-agentcore-itsm
```

Build the container image for ARM64 (required by AgentCore). If builder doesn't exist, create it:
```bash
docker buildx create --use --name agentcore-builder 2>/dev/null || docker buildx use agentcore-builder
docker buildx build --platform linux/arm64 -t bedrock-agentcore-itsm-agent --load .
```

Verify the image was created:
```bash
docker images | grep bedrock-agentcore-itsm-agent
```

### Step 3: ECR Repository Setup

Create an ECR repository and push your container.

Set repository name:
```bash
export REPO_NAME=bedrock-agentcore-itsm-agent-repo
```

Create ECR repository:
```bash
aws ecr create-repository \
    --repository-name $REPO_NAME \
    --region $AWS_REGION
```

Get your AWS account ID:
```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

Set the full image URI:
```bash
export IMAGE_TAG=latest
export IMAGE_URI=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:$IMAGE_TAG
```

Display the image URI:
```bash
echo "Image URI: $IMAGE_URI"
```

Push the container to ECR. Get ECR login token and login to Docker:
```bash
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

Tag your local image with the ECR URI:
```bash
docker tag bedrock-agentcore-itsm-agent:latest $IMAGE_URI
```

Push the image to ECR:
```bash
docker push $IMAGE_URI
```

Verify the push:
```bash
aws ecr describe-images --repository-name $REPO_NAME --region $AWS_REGION
```

### Step 4: CloudFormation Deployment

Deploy the CloudFormation stack.

Set deployment parameters:
```bash
export STACK_NAME=bedrock-agentcore-itsm
```

Build the SAM application:
```bash
sam build
```

Deploy the CloudFormation stack:
```bash
sam deploy \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $AWS_REGION \
    --resolve-s3
```

Monitor the deployment progress. Watch the deployment progress:
```bash
aws cloudformation describe-stack-events \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
    --output table
```

Check final deployment status:
```bash
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].StackStatus' \
    --output text
```

Get the Knowledge Base S3 bucket name:
```bash
export KB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseS3Bucket`].OutputValue' \
    --output text)
echo "Knowledge Base S3 Bucket: $KB_BUCKET"
```

Upload the PDF document to the Knowledge Base S3 bucket:
```bash
aws s3 cp ../../docs/Fictitious-Company-Employee-IT-Handbook.pdf s3://$KB_BUCKET/
```

Sync the Knowledge Base to index the uploaded document:
```bash
aws bedrock-agent start-ingestion-job \
    --knowledge-base-id $KNOWLEDGE_BASE_ID \
    --data-source-id $(aws bedrock-agent list-data-sources \
        --knowledge-base-id $KNOWLEDGE_BASE_ID \
        --region $AWS_REGION \
        --query 'dataSourceSummaries[0].dataSourceId' \
        --output text) \
    --region $AWS_REGION
```

Wait for the ingestion job to complete (this may take a few minutes):
```bash
aws bedrock-agent list-ingestion-jobs \
    --knowledge-base-id $KNOWLEDGE_BASE_ID \
    --data-source-id $(aws bedrock-agent list-data-sources \
        --knowledge-base-id $KNOWLEDGE_BASE_ID \
        --region $AWS_REGION \
        --query 'dataSourceSummaries[0].dataSourceId' \
        --output text) \
    --region $AWS_REGION \
    --query 'ingestionJobSummaries[0].status' \
    --output text
```

### Step 5: Create AgentCore Memory

Create a memory resource for conversation persistence using the AWS CLI:
```bash
aws bedrock-agentcore-control list-memories --region $AWS_REGION
```

If you don't have a memory resource yet, you can create one using the AgentCore SDK in Python or via the AWS Console. For this demo, we'll use an existing memory or create one programmatically.

Get the memory ID (if ITSMAgentMemory exists):
```bash
export MEMORY_ID=$(aws bedrock-agentcore-control list-memories --region $AWS_REGION --query 'memories[?starts_with(id, `ITSMAgentMemory`)].id | [0]' --output text)
```

If no memory exists, the agent will run in stateless mode. To create a memory resource, use the AWS Console or SDK.

Display the memory ID:
```bash
echo "Memory ID: $MEMORY_ID"
```

### Step 6: Create AgentCore Runtime

Get the required values from CloudFormation. Get Knowledge Base ID:
```bash
export KNOWLEDGE_BASE_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text)
```

Get API Gateway URL:
```bash
export API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)
```

Get Execution Role ARN:
```bash
export EXECUTION_ROLE_ARN=$(aws iam get-role \
    --role-name $STACK_NAME-AgentCoreExecutionRole \
    --query 'Role.Arn' \
    --output text)
```

Display the values:
```bash
echo "Knowledge Base ID: $KNOWLEDGE_BASE_ID"
echo "API Gateway URL: $API_GATEWAY_URL"
echo "Execution Role ARN: $EXECUTION_ROLE_ARN"
echo "Container Image URI: $IMAGE_URI"
```

Create the AgentCore runtime:
```bash
aws bedrock-agentcore-control create-agent-runtime \
    --agent-runtime-name bedrock_agentcore_itsm_runtime \
    --description "AgentCore Runtime for ITSM solution" \
    --role-arn $EXECUTION_ROLE_ARN \
    --agent-runtime-artifact containerConfiguration={containerUri=$IMAGE_URI} \
    --network-configuration networkMode=PUBLIC \
    --protocol-configuration serverProtocol=HTTP \
    --environment-variables KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID,API_GATEWAY_URL=$API_GATEWAY_URL,AWS_REGION=$AWS_REGION,MEMORY_ID=$MEMORY_ID \
    --region $AWS_REGION
```

Save the runtime ID from the output. Get the runtime ID from the create command output or list runtimes to find it:
```bash
aws bedrock-agentcore-control list-agent-runtimes --region $AWS_REGION
```

Set the runtime ID and ARN (replace with actual values from output):
```bash
export AGENT_RUNTIME_ID=<runtime-id-from-output>
export AGENT_RUNTIME_ARN=<runtime-arn-from-output>
```

Check if a default endpoint was created:
```bash
aws bedrock-agentcore-control list-agent-runtime-endpoints \
    --agent-runtime-id $AGENT_RUNTIME_ID \
    --region $AWS_REGION
```

### Step 7: Invoke the AgentCore Agent

Invoke the AgentCore agent with natural language. Create a payload file for ticket creation:
```bash
cat > payload.json << 'EOF'
{
  "prompt": "Create a high priority incident ticket for a server outage in production",
  "session_id": "user-123"
}
EOF
```

**Note:** The `session_id` parameter enables conversation memory. Use the same session_id across multiple requests to maintain context. If omitted, each request will be stateless.

Invoke the agent:
```bash
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn $AGENT_RUNTIME_ARN \
    --payload file://payload.json \
    --content-type application/json \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    output.json
```

View the response:
```bash
cat output.json
```

Query the knowledge base:
```bash
cat > payload.json << 'EOF'
{
  "prompt": "What is the password reset policy?",
  "session_id": "user-123"
}
EOF
```

```bash
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn $AGENT_RUNTIME_ARN \
    --payload file://payload.json \
    --content-type application/json \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    output.json
```

```bash
cat output.json
```

Look up a ticket:
```bash
cat > payload.json << 'EOF'
{
  "prompt": "Look up ticket INC12345678",
  "session_id": "user-123"
}
EOF
```

```bash
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn $AGENT_RUNTIME_ARN \
    --payload file://payload.json \
    --content-type application/json \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    output.json
```

```bash
cat output.json
```

The AgentCore agent will:
1. Understand your natural language request
2. Determine which tool to use (create ticket, lookup ticket, or query knowledge base)
3. Extract the required parameters from your request
4. Call the appropriate Lambda function via API Gateway
5. Return a natural language response
6. Store conversation context in memory when session_id is provided

**Using Memory for Conversations:**

AgentCore memory allows the agent to maintain context across multiple interactions. To use memory:

1. Include a `session_id` in your payload (e.g., user ID, conversation ID)
2. Use the same `session_id` for all requests in the same conversation
3. The agent will remember previous interactions and maintain context

Example conversation with memory:
```bash
# First request
cat > payload.json << 'EOF'
{
  "prompt": "I need help with my laptop",
  "session_id": "user-456"
}
EOF
```

```bash
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn $AGENT_RUNTIME_ARN \
    --payload file://payload.json \
    --content-type application/json \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    output.json
```

```bash
# Follow-up request (agent remembers the laptop context)
cat > payload.json << 'EOF'
{
  "prompt": "Create a ticket for it",
  "session_id": "user-456"
}
EOF
```

```bash
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn $AGENT_RUNTIME_ARN \
    --payload file://payload.json \
    --content-type application/json \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    output.json
```

The agent will understand "it" refers to the laptop issue from the previous message.

**Troubleshooting:** If you get a 404 error, check the CloudWatch logs.

Get the log group name for your runtime:
```bash
aws logs describe-log-groups \
    --log-group-name-prefix /aws/bedrock-agentcore \
    --region $AWS_REGION
```

View recent logs:
```bash
aws logs tail /aws/bedrock-agentcore/bedrock_agentcore_itsm_runtime \
    --follow \
    --region $AWS_REGION
```

Common issues:
- The container must expose `/invocations` POST and `/ping` GET endpoints
- The container must be built for ARM64 architecture
- Check that environment variables are set correctly in the runtime
- Verify the execution role has permissions to invoke Bedrock models and access resources

**Updating the AgentCore Image:**

If you need to update the agent code and redeploy, navigate to the directory:
```bash
cd src/bedrock-agentcore-itsm
```

Rebuild the image:
```bash
docker buildx build --platform linux/arm64 -t bedrock-agentcore-itsm-agent --load .
```

Tag and push to ECR:
```bash
docker tag bedrock-agentcore-itsm-agent:latest $IMAGE_URI
docker push $IMAGE_URI
```

Update the runtime with the new image (including MEMORY_ID):
```bash
aws bedrock-agentcore-control update-agent-runtime \
    --agent-runtime-id $AGENT_RUNTIME_ID \
    --role-arn $EXECUTION_ROLE_ARN \
    --agent-runtime-artifact containerConfiguration={containerUri=$IMAGE_URI} \
    --network-configuration networkMode=PUBLIC \
    --environment-variables KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID,API_GATEWAY_URL=$API_GATEWAY_URL,AWS_REGION=$AWS_REGION,MEMORY_ID=$MEMORY_ID \
    --region $AWS_REGION
```

### Step 8: Deploy Chat Application

The chat application is shared between both implementations and supports both Bedrock Agents and AgentCore backends.

Navigate to the chat app directory:
```bash
cd ../chat-app
```

Build the application:
```bash
sam build
```

For AgentCore deployment, use the runtime ARN (already set in Step 6):
```bash
echo "AgentCore Runtime ARN: $AGENT_RUNTIME_ARN"
```

Deploy with AgentCore configuration:
```bash
sam deploy \
    --stack-name bedrock-agent-chat-app \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $AWS_REGION \
    --parameter-overrides \
        ImplementationType=bedrock-agentcore \
        AgentCoreEndpoint=$AGENT_RUNTIME_ARN \
    --resolve-s3
```

Get the S3 bucket name from CloudFormation outputs:
```bash
export WEB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name bedrock-agent-chat-app \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)
```

Upload web files:
```bash
aws s3 cp web/ s3://$WEB_BUCKET/ --recursive
```

Get the CloudFront URL:
```bash
aws cloudformation describe-stacks \
    --stack-name bedrock-agent-chat-app \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' \
    --output text
```

Access the chat application at the CloudFront URL. You'll need to create a Cognito user to log in.

### Understanding the Components

### Agent Implementation (`agent_runtime.py`)
The main agent implementation using the Strands framework that orchestrates tool usage and handles user requests with memory support.

### Tools
Defined as Python functions with the `@tool` decorator:
* **create_ticket**: Handles ticket creation requests with IAM-authenticated API calls
* **lookup_ticket**: Handles ticket lookup requests
* **query_knowledge_base**: Queries the Bedrock Knowledge Base for IT policies and procedures

### Shared Functions (`functions/`)
Lambda functions that provide the ITSM API backend, shared with the Bedrock Agents implementation for data compatibility.

### Infrastructure (`template.yml`)
CloudFormation template that defines the AgentCore execution role, shared resources (DynamoDB, S3, OpenSearch, Knowledge Base), and IAM permissions.

## Troubleshooting

### Container Build Issues

Check Docker daemon:
```bash
docker info
```

Clean Docker cache:
```bash
docker system prune -f
```

Rebuild without cache:
```bash
docker build --no-cache -t bedrock-agentcore-itsm-agent .
```

### ECR Push Issues

Re-authenticate with ECR:
```bash
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

Verify repository exists:
```bash
aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION
```

### CloudFormation Issues

Check detailed error messages:
```bash
aws cloudformation describe-stack-events \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[ResourceStatusReason,LogicalResourceId]' \
    --output table
```

## Rollback

To rollback the deployment, delete CloudFormation stack:
```bash
aws cloudformation delete-stack \
    --stack-name $STACK_NAME \
    --region $AWS_REGION
```

Clean up ECR repository (optional):
```bash
aws ecr delete-repository \
    --repository-name $REPO_NAME \
    --region $AWS_REGION \
    --force
```

Clean up local Docker images:
```bash
docker rmi bedrock-agentcore-itsm-agent:latest $IMAGE_URI
```

## Learning Objectives

By completing this deployment, you'll gain:

* Container-based AI agent deployment experience with Amazon Bedrock AgentCore
* ECR repository management and Docker workflows
* CloudFormation parameter management
* AWS service integration and IAM permission management
* Debugging and monitoring capabilities for containerized applications
* Infrastructure as Code best practices

## Next Steps

After successful deployment:

1. **Explore the Code**: Examine the agent and tool implementations
2. **Customize the Agent**: Modify the agent logic for your use cases
3. **Add New Tools**: Extend the agent with additional capabilities
4. **Monitor Performance**: Set up CloudWatch dashboards and alarms
5. **Security Review**: Review IAM permissions and implement security best practices
6. **Scale for Production**: Configure auto-scaling and high-availability settings for production workloads

This approach provides the foundation for building AI applications with AgentCore's enterprise-grade platform.