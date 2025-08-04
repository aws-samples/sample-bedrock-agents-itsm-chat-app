// CommonJS module
const { BedrockAgentRuntimeClient, InvokeAgentCommand } = require("@aws-sdk/client-bedrock-agent-runtime");
const { randomUUID } = require('crypto');

exports.handler = async (event) => {
  const client = new BedrockAgentRuntimeClient(process.env.AWS_REGION);

  console.log(event.toString());

  try {
    var sessionId = event['sessionId'];

    if (sessionId == "default") {
      var sessionId = generateSessionId();
    }
  } catch (error) {
    var sessionId = generateSessionId();
  }

  var agentAliasId = process.env.agentAliasId;
  var agentId = process.env.agentId;
  var inputText = event['inputText'];

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

  var final = {
    sessionId: sessionId,
    response: finalResponse
  };

  return final; 
};

function generateSessionId() {
  return randomUUID();
}