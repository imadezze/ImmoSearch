# ImmoSearch

MCP server exposing DVF (Demandes de Valeurs Foncières) analysis tools for French real estate data. This project includes both a powerful MCP server for property analysis and a beautiful conversational UI for apartment viewing reservations.

## Features

- 🏠 **Real Estate Analysis**: DVF data analysis with property search and filtering
- 🚗 **Travel Time Calculations**: Automatic commute time calculations to workplace
- 📍 **Location Services**: Reverse geocoding and address lookup
- 💬 **Conversational UI**: Elegant apartment viewing assistant interface
- 📊 **Metrics Integration**: W&B integration for analytics and tracing
- 🌐 **Multiple Interfaces**: Both MCP server and FastAPI web interface

## Project Structure

- `mcp_servers/immosearch_server.py` - Main MCP server for real estate analysis
- `conversationImmoSearch/` - FastAPI web interface with conversational UI
- `voiceassistant/` - LiveKit voice assistant integration
- `scripts/` - Utility scripts for data processing and integrations

## Running the MCP Server

In order to run your MCP server locally, use the following command:

```bash
python -m mcp_servers.immosearch_server
```

The server will automatically start in **streamable HTTP** mode

## Running the Conversational UI

To run the FastAPI web interface with the apartment viewing assistant:

```bash
cd conversationImmoSearch
python app.py
```

Then visit `http://localhost:7860` to access the conversational interface.

## Deployment Commands

For deployment platforms (like Hugging Face Spaces), use these commands:

### Using uv (recommended):
**Install command:**
```bash
uv sync --frozen --no-dev
```

**Start command:**
```bash
python mcp_servers/immosearch_server.py
```

### Using pip (alternative):
**Install command:**
```bash
pip install -r requirements.txt
```

**Start command:**
```bash
python mcp_servers/immosearch_server.py
```

## Exposing the Server

If you want to expose the server to be visible globally, you can use [ngrok]()

```bash
ngrok http [Port Number]
```

You can then use the resulting public address to integrate your MCP server into an existing platform (e.g. Mistral LeChat).


