# Run the MCP Server in Docker

This image runs the MCP server over Streamable HTTP at `http://localhost:8000/mcp`.

## Prerequisites

- Docker Desktop is installed and running.
- Run the commands below from the project root.

## Build the image

```powershell
docker build -t deccansoft-institute-mcp .
```

## Create and seed persistent data

The server uses SQLite. Create a named Docker volume so data survives container replacement, then seed it once with the sample data.

```powershell
docker volume create deccansoft-mcp-data
docker run --rm -v deccansoft-mcp-data:/app/data deccansoft-institute-mcp python seed_data.py
```

Skip the seed command when starting with an empty database. Do not run it again against an already-seeded volume because the sample records have unique email addresses.

## Start the server

```powershell
docker run --detach --name deccansoft-mcp-server --publish 8000:8000 --volume deccansoft-mcp-data:/app/data deccansoft-institute-mcp
```

Follow the server logs:

```powershell
docker logs --follow deccansoft-mcp-server
```

Stop and remove the server container. The named volume, and therefore the database, remains intact.

```powershell
docker stop deccansoft-mcp-server
docker rm deccansoft-mcp-server
```

## Connect an MCP client

Configure a Streamable HTTP connection with this server URL:

```text
http://localhost:8000/mcp
```

For a client running in another Docker container on the same Docker network, use the MCP container name and port instead:

```text
http://deccansoft-mcp-server:8000/mcp
```

## Remove persistent data

This permanently deletes the database:

```powershell
docker volume rm deccansoft-mcp-data
```