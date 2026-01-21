# Bedrock AgentCore ITSM Implementation

This directory contains the Bedrock AgentCore implementation of the ITSM chat solution. This approach uses a container-based runtime designed for production deployments that require enterprise-grade customization, control, and integration with frameworks like LangChain, LangGraph, and Strands.

## Overview

The AgentCore implementation provides:

* **Production-Ready Architecture**: Enterprise-grade deployment with full control over agent behavior
* **Custom Agent Logic**: Complete control using Python and the Strands framework
* **Container-Based Deployment**: Modern containerized deployment patterns for production environments
* **Framework Flexibility**: Use any Python AI framework (LangChain, LangGraph, Strands, etc.)
* **Advanced Debugging**: Direct access to agent code for debugging and monitoring
* **Enterprise Security**: Compliance-ready with custom security controls

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

The AgentCore deployment is designed for production environments. You'll execute each step to understand and control the container-based AI agent deployment process.

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

**Note:** The Dockerfile is included in the repository but is in .gitignore to prevent accidental commits of customized versions. If you need to recreate it, use the following command.

Create a Dockerfile for the AgentCore runtime:
```bash
cat > Dockerfile << 'EOF'
# AgentCore requires ARM64 architecture
FROM --platform=linux/arm64 python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent_runtime.py .

# Expose port 8080
EXPOSE 8080

# Run the AgentCore Runtime server
# The app object is defined in agent_runtime.py
CMD ["python", "-m", "uvicorn", "agent_runtime:app", "--host", "0.0.0.0", "--port", "8080"]
EOF
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

### Step 5: Create AgentCore Runtime

**Note:** Bedrock AgentCore requires ARM64 architecture for container images. The AgentCore runtime will be created using the AWS CLI.

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
    --environment-variables KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID,API_GATEWAY_URL=$API_GATEWAY_URL,AWS_REGION=$AWS_REGION \
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

If no endpoint exists, create one (optional - a default endpoint is usually created automatically):
```bash
aws bedrock-agentcore-control create-agent-runtime-endpoint \
    --agent-runtime-id $AGENT_RUNTIME_ID \
    --name bedrock_agentcore_itsm_endpoint \
    --region $AWS_REGION
```

**Note:** Multiple endpoints can be useful for different environments (dev, staging, prod) or for A/B testing different agent versions.

### Step 6: Verify Deployment

Get the stack outputs. Get all stack outputs:
```bash
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table
```

Get the API Gateway URL:
```bash
export API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)
```

Display the API Gateway URL:
```bash
echo "API Gateway URL: $API_GATEWAY_URL"
```

Test the underlying Lambda functions (optional). Test ticket creation Lambda directly:
```bash
aws lambda invoke \
    --function-name $STACK_NAME-ITSM-Create \
    --payload '{"tickettype":"INC","description":"Test ticket","impact":"Low","urgency":"Low"}' \
    --region $AWS_REGION \
    response.json
```

View the response:
```bash
cat response.json
```

### Step 7: Invoke the AgentCore Agent

Get the agent runtime ARN. List runtimes to get the ARN:
```bash
aws bedrock-agentcore-control list-agent-runtimes --region $AWS_REGION
```

Set the runtime ARN (replace with actual value from output):
```bash
export AGENT_RUNTIME_ARN=<runtime-arn-from-list>
```

Invoke the AgentCore agent with natural language. Create a payload file for ticket creation:
```bash
cat > payload.json << 'EOF'
{
  "prompt": "Create a high priority incident ticket for a server outage in production"
}
EOF
```

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
  "prompt": "What is the password reset policy?"
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
  "prompt": "Look up ticket INC12345678"
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

Update the runtime with the new image:
```bash
aws bedrock-agentcore-control update-agent-runtime \
    --agent-runtime-id $AGENT_RUNTIME_ID \
    --role-arn $EXECUTION_ROLE_ARN \
    --agent-runtime-artifact containerConfiguration={containerUri=$IMAGE_URI} \
    --network-configuration networkMode=PUBLIC \
    --region $AWS_REGION
```

### Step 8: Deploy Chat Application

The chat application is shared between both implementations. Navigate to the chat app directory and deploy:
```bash
cd ../chat-app
```

```bash
sam build
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
```

Upload the web files. Get the S3 bucket name from CloudFormation outputs:
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

## Understanding the Components

### Agent Implementation (`agent/strands_agent.py`)
The main agent class that orchestrates tool usage and handles user requests using the Strands framework.

### Tools (`agent/tools/`)
* **create_ticket.py**: Handles ticket creation requests
* **lookup_ticket.py**: Handles ticket lookup requests  
* **knowledge_base.py**: Handles knowledge base queries

### Shared Functions (`functions/`)
Lambda functions that provide the same ITSM API as the Bedrock Agents implementation, ensuring data compatibility.

### Infrastructure (`template.yml`)
CloudFormation template that defines the AgentCore runtime, shared resources, and IAM permissions.

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

* Production-ready container-based AI agent deployment experience
* ECR repository management and Docker workflows for enterprise environments
* CloudFormation parameter management for production deployments
* AWS service integration and enterprise IAM permission management
* Debugging and monitoring capabilities for containerized applications
* Infrastructure as Code best practices for production systems

## Next Steps

After successful deployment:

1. **Explore the Code**: Examine the production-ready agent and tool implementations
2. **Customize the Agent**: Modify the agent logic for your enterprise use cases
3. **Add New Tools**: Extend the agent with additional enterprise capabilities
4. **Monitor Performance**: Set up production-grade CloudWatch dashboards and alarms
5. **Security Review**: Review IAM permissions and implement enterprise security configurations
6. **Scale for Production**: Configure auto-scaling and high-availability settings

This production-focused approach provides the foundation for building enterprise-ready AI applications with full control and customization capabilities.