// CommonJS module
const { BedrockAgentRuntimeClient, InvokeAgentCommand } = require("@aws-sdk/client-bedrock-agent-runtime");
const { randomUUID } = require('crypto');

exports.handler = async (event) => {
  console.log('Event received:', JSON.stringify(event));

  try {
    var sessionId = event['sessionId'];
    if (sessionId == "default") {
      sessionId = generateSessionId();
    }
  } catch (error) {
    sessionId = generateSessionId();
  }

  var inputText = event['inputText'];
  const implementationType = process.env.IMPLEMENTATION_TYPE;

  console.log('Implementation type:', implementationType);

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
  const https = require('https');
  const agentCoreEndpoint = process.env.AGENTCORE_ENDPOINT;
  
  if (!agentCoreEndpoint) {
    throw new Error('AGENTCORE_ENDPOINT environment variable is required for bedrock-agentcore implementation');
  }

  const requestBody = JSON.stringify({
    inputText: inputText,
    sessionId: sessionId
  });

  const options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(requestBody)
    }
  };

  return new Promise((resolve, reject) => {
    const req = https.request(agentCoreEndpoint, options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          resolve({
            sessionId: sessionId,
            response: response.response || response.message || 'No response received'
          });
        } catch (error) {
          console.error('Error parsing AgentCore response:', error);
          resolve({
            sessionId: sessionId,
            response: 'Error processing request'
          });
        }
      });
    });

    req.on('error', (error) => {
      console.error('Error calling AgentCore:', error);
      resolve({
        sessionId: sessionId,
        response: 'Error connecting to agent service'
      });
    });

    req.write(requestBody);
    req.end();
  });
}

function generateSessionId() {
  return randomUUID();
}