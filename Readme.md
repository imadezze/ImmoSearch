# ImmoSearch

## Running the Server

In order to run your MCP server locally, use the following command:

> python -m mcp_servers.leboncoin_server

The server will automatically start in **streamable HTTP** mode

## Exposing the Server

If you want to expose the server to be visible globally, you can use [ngrok]()

> ngrok http [Port Number]

You can then use the resulting public address to integrate your MCP server into an existing platform (e.g. Mistral LeChat).


