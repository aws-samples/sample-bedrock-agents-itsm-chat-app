# Bedrock Agent Chat Application

This sample solution demonstrates how Amazon Bedrock Agents can streamline internal IT service management processes through natural language interactions. By leveraging agentic flows, the sample showcases how Generative AI can automate the complex task of navigating ticketing systems, identifying appropriate workflows, and executing actions through ITSM APIs. The solution enables internal stakeholders to effortlessly create tickets, initiate projects, and manage approvals through simple conversations, reducing manual effort and improving efficiency in organizational processes.

This solution provides a web-based chat interface for interacting with an Amazon Bedrock Agent. It includes a complete serverless architecture with authentication, API, and frontend components.

![Architecture Diagram](docs/bedrock-agents-itsm.png)

This project includes the following files and folders:

- * **docs** - Directory containing supporting documents
- * **src/bedrock-agent-itsm** - Directory containing a SAM template to deploy the Bedrock Agent ITSM resources
- * **src/chat-app** - Directory containing a SAM template to deploy the chat application frontend and API
- * **src/chat-app/web** - Directory containing the web application code for the chat interface

## Prerequisites

Before deploying the application, ensure you have the necessary tools installed as described in the Deployment Instructions section.

## Deployment Instructions

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools:

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* Node.js - [Install Node.js](https://nodejs.org/en/), including the NPM package management tool.
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

The deployment process consists of three main steps:

1. First, deploy the Bedrock Agent ITSM template
2. Upload PDF documents to the S3 bucket and sync the Knowledge Base
3. Then, deploy the chat application template
4. Last, upload the web files to the S3 web bucket

### Step 1: Deploy the Bedrock Agent ITSM Template

Navigate to the **src/bedrock-agent-itsm** directory and run the following commands:

```bash
sam build
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
```

During the guided deployment, you'll be prompted for several parameters:

* **Stack Name**: The name of the stack to deploy to CloudFormation (e.g., bedrock-agent-itsm).
* **AWS Region**: The region to deploy your resources.

* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates create AWS IAM roles required for the Lambda functions to access AWS services.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project.

After the deployment completes, note the outputs from the CloudFormation stack, as you'll need the Bedrock Knowledge Base and S3 bucket name for the next steps.

### Step 2: Upload PDF Documents and Sync Knowledge Base

1. Upload the PDF documents from the **docs** folder to the S3 bucket created by the template:

```bash
aws s3 cp docs/ s3://<your-knowledge-base-bucket-name>/ --recursive --exclude "*" --include "*.pdf"
```

2. Navigate to the Amazon Bedrock console, go to Knowledge bases, select the knowledge base created by the template, and click on "Sync" to update the data source with the newly uploaded documents.

### Step 3: Deploy the Chat Application Template

Navigate to the **src/chat-app** directory and run the following commands:

```bash
sam build
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
```

During the guided deployment, you'll be prompted for several parameters:

* **Stack Name**: The name of the stack to deploy to CloudFormation (e.g., bedrock-agent-chat-app).
* **AWS Region**: The region to deploy your resources.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates create AWS IAM roles required for the Lambda functions to access AWS services.
* **Disable rollback**: By default, if there's an error during a deployment, your CloudFormation stack rolls back to the last stable state.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project.

### Step 4: Upload Web Files to S3 Bucket

After the chat application deployment completes, you need to upload the web application files to the S3 bucket created by the template:

1. Note the S3 bucket name from the CloudFormation outputs (S3BucketName).
2. Upload the web files from the **src/chat-app/web** directory to the S3 bucket:

```bash
aws s3 cp src/chat-app/web/ s3://<your-website-bucket-name>/ --recursive
```

### Step 5 (Optional): 
As a best practice, you should update the API Gateway CORS setting (Access-Control-Allow-Origin) to reflect the domain of the chat-app instead of a wildcard domain ('*') to mitigate potential XSS attacks.  Refer to the CORS documentation for more information:  https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html

## Subsequent Deployments

After the initial guided deployment, you can use the following commands for subsequent deployments:

```bash
# For the Bedrock Agent ITSM template
cd src/bedrock-agent-itsm
sam build
sam deploy --capabilities CAPABILITY_NAMED_IAM

# For the Chat Application template
cd src/chat-app
sam build
sam deploy --capabilities CAPABILITY_NAMED_IAM
```

**Note**: The `--capabilities CAPABILITY_NAMED_IAM` flag is required because the templates create IAM resources with specific names. Without this flag, deployment will fail with an error message indicating that the capability is required.

## Accessing the Chat Application

After deployment completes, you can find the CloudFront URL in the outputs section of the Chat App CloudFormation stack. Navigate to this URL in your browser to access the chat application.

You'll need to create a user account through the Cognito user pool before you can log in and start chatting with the Bedrock Agent.

## Architecture

This application is composed of two main components, each defined by its own SAM template:

### Bedrock Agent ITSM Architecture

The Bedrock Agent ITSM template (`src/bedrock-agent-itsm/template.yml`) deploys the following AWS resources:

* **Amazon Bedrock Agent** - Creates an agent with knowledge bases and action groups
* **Amazon Bedrock Knowledge Base** - Stores and indexes documents for agent retrieval
* **Amazon OpenSearch Serverless** - Vector database for the knowledge base
* **Amazon DynamoDB** - Table for storing mock ITSM ticket information
* **AWS Lambda Functions**:
  * ITSM ticket creation and lookup functions
  * Bedrock agent action group handler functions
  * OpenSearch index creation function
  * Bedrock model entitlement function
* **Amazon API Gateway** - REST API for ITSM ticket operations
* **Amazon S3** - Bucket for knowledge base documents
* **AWS IAM Roles** - Various roles for Bedrock, Lambda, and OpenSearch permissions


### Chat Application Architecture

The Chat Application template (`src/chat-app/template.yml`) deploys the following AWS resources:

* **AWS Lambda** - Function that communicates with the Bedrock Agent
* **Amazon API Gateway** - REST API with Cognito authorization
* **Amazon Cognito** - User pool and client for authentication
* **Amazon CloudFront** - Distribution for delivering the web application
* **Amazon S3** - Bucket for hosting the static web content
* **AWS IAM Roles** - Execution roles for Lambda functions
* **Custom Resources** - Lambda function to generate frontend configuration

Both templates use AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
bedrock-agent-chat-app$ sam logs -n ChatLambdaFunction --stack-name bedrock-agent-chat-app --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name bedrock-agent-chat-app
aws cloudformation delete-stack --stack-name bedrock-agent-itsm
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)


If you prefer to use an integrated development environment (IDE) to build and test your application, you can use the AWS Toolkit.  
The AWS Toolkit is an open source plug-in for popular IDEs that uses the SAM CLI to build and deploy serverless applications on AWS. The AWS Toolkit also adds a simplified step-through debugging experience for Lambda function code. See the following links to get started.

* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [Visual Studio](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/welcome.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.