// CommonJS module
const { BedrockAgentRuntimeClient, InvokeAgentCommand } = require("@aws-sdk/client-bedrock-agent-runtime");
const { randomUUID } = require('crypto');

exports.handler = async (event) => {
  const token = event.token;
  
  if (!token) {
    return {
      statusCode: 401,
      body: JSON.stringify({ error: 'Unauthorized - No token provided' })
    };
  }

  let cognitoUserId;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid token format');
    }
    
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString('utf8'));
    cognitoUserId = payload['cognito:username'];
    
    if (!cognitoUserId) {
      throw new Error('cognito:username not found in token');
    }
  } catch (error) {
    return {
      statusCode: 401,
      body: JSON.stringify({ error: 'Unauthorized - Invalid token' })
    };
  }

  const sessionId = cognitoUserId;
  const inputText = event['inputText'];
  const implementationType = process.env.IMPLEMENTATION_TYPE;

  if (implementationType === 'bedrock-agents') {
    return await handleBedrockAgents(inputText, sessionId);
  } else if (implementationType === 'bedrock-agentcore') {
    return await handleBedrockAgentCore(inputText, sessionId);
  } else {
    throw new Error(`Unknown implementation type: ${implementationType}`);
  }
};

async function handleBedrockAgents(inputText, sessionId) {
  const client = new BedrockAgentRuntimeClient({ region: process.env.AWS_REGION });
  
  var agentAliasId = process.env.agentAliasId;
  var agentId = process.env.agentId;

  const input = {
    agentId: agentId,
    agentAliasId: agentAliasId,
    sessionId: sessionId,
    enableTrace: false,
    inputText: inputText,
    streamFinalResponse: false
  };

  const command = new InvokeAgentCommand(input);
  const response = await client.send(command);
  
  let finalResponse = '';
  
  for await (const chunk of response.completion) {
    if (chunk.chunk?.bytes) {
      const text = new TextDecoder().decode(chunk.chunk.bytes);
      finalResponse += text;
    }
  }

  return {
    sessionId: sessionId,
    response: finalResponse
  };
}

async function handleBedrockAgentCore(inputText, sessionId) {
  const { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } = require("@aws-sdk/client-bedrock-agentcore");
  const { randomUUID } = require('crypto');
  
  const agentRuntimeArn = process.env.AGENTCORE_ENDPOINT;
  
  if (!agentRuntimeArn) {
    throw new Error('AGENTCORE_ENDPOINT environment variable is required for bedrock-agentcore implementation');
  }

  const client = new BedrockAgentCoreClient({ region: process.env.AWS_REGION });

  const runtimeSessionId = sessionId && sessionId.length >= 33 
    ? sessionId 
    : `session-${randomUUID()}-${Date.now()}`;

  const payload = JSON.stringify({
    prompt: inputText,
    session_id: runtimeSessionId
  });

  const command = new InvokeAgentRuntimeCommand({
    agentRuntimeArn: agentRuntimeArn,
    runtimeSessionId: runtimeSessionId,
    payload: Buffer.from(payload)
  });

  try {
    const response = await client.send(command);
    
    if (response.response) {
      let fullResponse = '';
      
      for await (const chunk of response.response) {
        if (chunk) {
          const part = new TextDecoder().decode(chunk);
          fullResponse += part;
        }
      }
      
      if (fullResponse) {
        try {
          const responseBody = JSON.parse(fullResponse);
          let responseText = fullResponse;
          if (responseBody.message && responseBody.message.content && responseBody.message.content[0]) {
            responseText = responseBody.message.content[0].text;
          } else if (responseBody.message) {
            responseText = responseBody.message;
          } else if (responseBody.response) {
            responseText = responseBody.response;
          }
          
          return {
            sessionId: responseBody.session_id || runtimeSessionId,
            response: responseText
          };
        } catch {
          return {
            sessionId: runtimeSessionId,
            response: fullResponse
          };
        }
      }
    }
    
    return {
      sessionId: runtimeSessionId,
      response: 'No response received from agent'
    };
  } catch (error) {
    return {
      sessionId: runtimeSessionId,
      response: `Error: ${error.message}`
    };
  }
}