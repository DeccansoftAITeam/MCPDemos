import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(command="python", args=["test.py"])

async def main():
    async with stdio_client(server) as (r, w), ClientSession(r, w) as s:
        await s.initialize()

        # Test the resource access - All within the sandboxed root, should succeed
        readMeContent = await s.read_resource("docs://readme.txt")
        print("Resource:", readMeContent.contents[0].text)

        # Test the tools and resource access - All within the sandboxed root, should succeed
        dirList = await s.call_tool("list_documents", arguments={"subdir": ""})
        print("List:", dirList.content[0].text)
        dirList = await s.call_tool("list_documents", arguments={"subdir": "notes"})
        print("List:", dirList.content[0].text)
        fileContent = await s.call_tool("read_file", arguments={"filepath": "readme.txt"})
        print("Read:", fileContent.content[0].text)
        fileContent = await s.call_tool("read_file", arguments={"filepath": "notes\\todo.txt"})
        print("Read:", fileContent.content[0].text)

        # Test path containment - Attempt to escape the sandbox, should fail
        dirList = await s.call_tool("list_documents", arguments={"subdir": "not-in-documents"})
        print("List:", dirList.content[0].text)
        notesContent = await s.call_tool("read_file", arguments={"filepath": "..\\not-in-documents\\todo.txt"})
        print("Escape:", notesContent.isError, notesContent.content[0].text)

asyncio.run(main())