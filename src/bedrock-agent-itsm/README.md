# Bedrock Agents Implementation Deployment Guide

This guide provides detailed deployment instructions for the Bedrock Agents implementation - a fully managed solution that's ideal for rapid prototyping and proof-of-concept development.

## Prerequisites

Before deploying the Bedrock Agents implementation, ensure you have the following tools installed:

* **SAM CLI** - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* **Node.js** - [Install Node.js](https://nodejs.org/en/), including the NPM package management tool
* **Docker** - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)
* **AWS CLI** - [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and configure with appropriate credentials

## Architecture

![Architecture Diagram](docs/bedrock-agents-itsm.png)

## Deployment Process

The deployment process consists of four main steps:

1. Deploy the Bedrock Agent ITSM template
2. Upload PDF documents to the S3 bucket and sync the Knowledge Base
3. Deploy the chat application template (see [chat-app README](../chat-app/README.md))
4. Upload the web files to the S3 web bucket

### Step 1: Deploy the Bedrock Agent ITSM Template

Navigate to the **src/bedrock-agent-itsm** directory and run the following commands:

```bash
cd src/bedrock-agent-itsm
sam build
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
```

During the guided deployment, you'll be prompted for several parameters:

* **Stack Name**: The name of the stack to deploy to CloudFormation (e.g., `bedrock-agent-itsm`)
* **AWS Region**: The region to deploy your resources
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates create AWS IAM roles required for the Lambda functions to access AWS services
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project

After the deployment completes, note the outputs from the CloudFormation stack, as you'll need the Bedrock Knowledge Base and S3 bucket name for the next steps.

### Step 2: Upload PDF Documents and Sync Knowledge Base

1. Upload the PDF documents from the **docs** folder to the S3 bucket created by the template:

```bash
aws s3 cp docs/ s3://<your-knowledge-base-bucket-name>/ --recursive --exclude "*" --include "*.pdf"
```

2. Navigate to the Amazon Bedrock console, go to Knowledge bases, select the knowledge base created by the template, and click on "Sync" to update the data source with the newly uploaded documents.

### Step 3: Deploy the Chat Application

Follow the deployment instructions in [src/chat-app/README.md](../chat-app/README.md) to deploy the shared chat application frontend.

## Subsequent Deployments

After the initial guided deployment, you can use the following commands for subsequent deployments:

```bash
cd src/bedrock-agent-itsm
sam build
sam deploy --capabilities CAPABILITY_NAMED_IAM
```

**Note**: The `--capabilities CAPABILITY_NAMED_IAM` flag is required because the templates create IAM resources with specific names. Without this flag, deployment will fail with an error message indicating that the capability is required.

## Architecture

The Bedrock Agents implementation creates a fully managed solution optimized for rapid prototyping with the following AWS resources:

* **Amazon Bedrock Agent** - Managed agent with built-in orchestration
* **Amazon Bedrock Knowledge Base** - Automated document indexing and retrieval
* **Action Groups** - Predefined integrations with Lambda functions
* **Amazon OpenSearch Serverless** - Managed vector database
* **Amazon DynamoDB** - Ticket storage table
* **AWS Lambda Functions** - ITSM operations and agent action handlers
* **Amazon API Gateway** - REST API for ticket operations
* **Amazon S3** - Knowledge base document storage
* **AWS IAM Roles** - Managed permissions for all services

## Troubleshooting

### Common Issues

1. **Deployment fails with IAM permissions error**
   - Ensure you're using `--capabilities CAPABILITY_NAMED_IAM` flag
   - Verify your AWS credentials have sufficient permissions

2. **Knowledge Base sync fails**
   - Verify PDF documents were uploaded to the correct S3 bucket
   - Check that the documents are in supported format (PDF)
   - Ensure the Bedrock service has permissions to access the S3 bucket

3. **Agent responses are not accurate**
   - Verify the Knowledge Base has been synced after uploading documents
   - Check that the documents contain relevant ITSM information
   - Review the agent instructions and action group configurations

### Logs and Monitoring

Use SAM CLI to fetch logs from your Lambda functions:

```bash
sam logs -n CreateITSMFunction --stack-name bedrock-agent-itsm --tail
sam logs -n LookupITSMFunction --stack-name bedrock-agent-itsm --tail
```

You can also monitor the Bedrock Agent performance through the AWS Console:
- Navigate to Amazon Bedrock > Agents
- Select your agent and view the execution logs and metrics

## Next Steps

After successful deployment:

1. Deploy the chat application using [src/chat-app/README.md](../chat-app/README.md)
2. Test the ITSM functionality through the chat interface
3. Customize the agent instructions and action groups as needed
4. Add additional PDF documents to expand the knowledge base

## Security Considerations

- Update API Gateway CORS settings to reflect your domain instead of wildcard ('*')
- Review IAM roles and permissions for least privilege access
- Enable CloudTrail logging for audit purposes
- Consider enabling AWS Config for compliance monitoring