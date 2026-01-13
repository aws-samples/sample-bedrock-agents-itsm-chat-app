const { DynamoDBClient } = require ("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, GetCommand } = require ("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

module.exports.handler = async (event) => {
  const ticketNumber = event.ticketNumber;
  
  // Define params for GetCommand with ticketNumber as primary key
  const params = {
    TableName: process.env.TABLE_NAME,
    Key: {
      ticketNumber: ticketNumber
    }
  };

  try {
    const result = await docClient.send(new GetCommand(params));
    
    if (result.Item) {
      const ticket = result.Item;
      const response = {
        statusCode: 200,
        ticketStatus: ticket.ticketStatus,
        ticketDesc: ticket.ticketDesc,
        ticketImpact: ticket.ticketImpact,
        ticketUrgency: ticket.ticketUrgency,
        createdAt: ticket.createdAt
      };
      return response;
    } else {
      return {
        statusCode: 200,
        ticketStatus: `Ticket not found for ticketNumber: ${ticketNumber}`,
      };
    }
  } catch (error) {
    console.error('Error retrieving ticket from DynamoDB:', error);
    return {
      statusCode: 500,
      ticketStatus: `Error retrieving ticket: ${ticketNumber}`,
    };
  }
};