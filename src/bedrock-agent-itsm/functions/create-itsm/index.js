const { DynamoDBClient } = require ("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, PutCommand } = require ("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

module.exports.handler = async (event) => {
  const tickettype = event.tickettype;
  const desc = event.description;
  const impact = event.impact;
  const urgency = event.urgency;

  const mockticket = makeid(tickettype);

  // Store data in DynamoDB
  const params = {
    TableName: process.env.TABLE_NAME,
    Item: {
      ticketNumber: mockticket,
      ticketDesc: desc,
      ticketImpact: impact,
      ticketUrgency: urgency,
      ticketStatus: "Pending",
      createdAt: new Date().toISOString()
    }
  };

  try {
    await docClient.send(new PutCommand(params));
    console.log('Successfully stored ticket in DynamoDB:', mockticket);
  } catch (error) {
    console.error('Error storing ticket in DynamoDB:', error);
    return {
      statusCode: 500,
      body: 'Error creating ticket'
    };
  }

  const response = {
    statusCode: 200,
    ticketNumber: 'Ticket created: ' + mockticket,
  };
  return response;
};

function makeid(tickettype) {
  let text = "";
  const possible = "0123456789";

  for (let i = 0; i < 8; i++)
    text += possible.charAt(Math.floor(Math.random() * possible.length));

  text = tickettype.substring(0, 3) + text;
  return text;
}