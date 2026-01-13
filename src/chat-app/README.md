# Chat Application Deployment Guide

This guide provides detailed deployment instructions for the shared chat application frontend that works with both Bedrock Agents and AgentCore implementations.

## Prerequisites

Before deploying the chat application, ensure you have:

* **SAM CLI** - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* **Node.js** - [Install Node.js](https://nodejs.org/en/), including the NPM package management tool
* **Docker** - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)
* **AWS CLI** - [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and configure with appropriate credentials
* **Backend Implementation** - Either Bedrock Agents or AgentCore must be deployed first

## Deployment Process

The chat application deployment consists of two main steps:

1. Deploy the chat application CloudFormation template
2. Upload the web application files to the S3 bucket

### Step 1: Deploy the Chat Application Template

Navigate to the **src/chat-app** directory and run the following commands:

```bash
cd src/chat-app
sam build
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
```

During the guided deployment, you'll be prompted for several parameters:

* **Stack Name**: The name of the stack to deploy to CloudFormation (e.g., `bedrock-agent-chat-app`)
* **AWS Region**: The region to deploy your resources (must match your backend implementation)
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates create AWS IAM roles required for the Lambda functions to access AWS services
* **Disable rollback**: By default, if there's an error during a deployment, your CloudFormation stack rolls back to the last stable state
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project

### Step 2: Upload Web Files to S3 Bucket

After the chat application deployment completes, you need to upload the web application files to the S3 bucket created by the template:

1. Note the S3 bucket name from the CloudFormation outputs (`S3BucketName`)
2. Upload the web files from the **src/chat-app/web** directory to the S3 bucket:

```bash
aws s3 cp src/chat-app/web/ s3://<your-website-bucket-name>/ --recursive
```

## Accessing the Chat Application

After deployment completes, you can find the CloudFront URL in the outputs section of the Chat App CloudFormation stack. Navigate to this URL in your browser to access the chat application.

You'll need to create a user account through the Cognito user pool before you can log in and start chatting with the Bedrock Agent.

## Subsequent Deployments

After the initial guided deployment, you can use the following commands for subsequent deployments:

```bash
cd src/chat-app
sam build
sam deploy --capabilities CAPABILITY_NAMED_IAM
```

**Note**: The `--capabilities CAPABILITY_NAMED_IAM` flag is required because the templates create IAM resources with specific names.

## Architecture

The Chat Application creates the following AWS resources:

* **AWS Lambda** - Function that communicates with either Bedrock Agent or AgentCore
* **Amazon API Gateway** - REST API with Cognito authorization
* **Amazon Cognito** - User pool and client for authentication
* **Amazon CloudFront** - CDN distribution for the web application
* **Amazon S3** - Static website hosting bucket
* **AWS IAM Roles** - Execution roles for Lambda functions
* **Custom Resources** - Lambda function to generate frontend configuration

## Integration with Backend Implementations

The chat application automatically detects which backend implementation is deployed and configures itself accordingly:

### With Bedrock Agents
- Connects directly to the Bedrock Agent via AWS SDK
- Uses the agent's session management capabilities
- Leverages built-in conversation memory

### With AgentCore
- Connects to the AgentCore Runtime endpoint
- Uses custom session management
- Integrates with container-based agent logic

## Troubleshooting

### Common Issues

1. **Deployment fails with IAM permissions error**
   - Ensure you're using `--capabilities CAPABILITY_NAMED_IAM` flag
   - Verify your AWS credentials have sufficient permissions

2. **Web files upload fails**
   - Verify the S3 bucket name from CloudFormation outputs
   - Check that you have write permissions to the S3 bucket
   - Ensure you're in the correct directory when running the upload command

3. **Chat application shows authentication errors**
   - Verify the Cognito User Pool was created successfully
   - Check that the CloudFront distribution is active
   - Ensure the backend implementation is deployed and accessible

4. **Chat responses are not working**
   - Verify that either Bedrock Agents or AgentCore backend is deployed
   - Check the Lambda function logs for connection errors
   - Ensure the API Gateway endpoints are accessible

### Logs and Monitoring

Use SAM CLI to fetch logs from the chat Lambda function:

```bash
sam logs -n ChatLambdaFunction --stack-name bedrock-agent-chat-app --tail
```

You can also monitor the application through the AWS Console:
- CloudWatch Logs for Lambda function execution
- API Gateway metrics for request/response monitoring
- CloudFront metrics for web application performance

## Security Configuration

### CORS Settings (Recommended)

As a best practice, you should update the API Gateway CORS setting (`Access-Control-Allow-Origin`) to reflect the domain of the chat-app instead of a wildcard domain ('*') to mitigate potential XSS attacks.

1. Navigate to API Gateway in the AWS Console
2. Select your chat application API
3. Update the CORS configuration to use your CloudFront domain
4. Redeploy the API

Refer to the [CORS documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html) for more information.

### Additional Security Considerations

- Enable CloudTrail logging for API calls
- Configure Cognito password policies according to your organization's requirements
- Review IAM roles and permissions for least privilege access
- Consider enabling AWS WAF for additional protection

## Customization

### Frontend Customization

The web application files are located in `src/chat-app/web/`:

- `index.html` - Main HTML structure
- `script.js` - JavaScript application logic
- `styles.css` - CSS styling
- `jquery-3.7.1.min.js` - jQuery library

After making changes to these files, re-upload them to the S3 bucket:

```bash
aws s3 cp src/chat-app/web/ s3://<your-website-bucket-name>/ --recursive
```

### Backend Integration

To modify how the chat application integrates with your backend:

1. Edit the Lambda function code in the CloudFormation template
2. Update the API Gateway configuration as needed
3. Redeploy using `sam deploy`

## Next Steps

After successful deployment:

1. Create user accounts in the Cognito User Pool
2. Test the chat functionality with your backend implementation
3. Customize the frontend appearance and branding
4. Configure additional security settings as needed
5. Set up monitoring and alerting for production use