# ait

**Archive of Interconnected Terms** - A local-first MCP server for ontology work.

## Usage

```bash
# Start MCP server for Claude Code
ait serve

# Check local store status
ait status

# Query local store
ait query "SELECT * WHERE { ?s ?p ?o } LIMIT 10"
```

## Claude Code Integration

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "ait": {
      "command": "ait",
      "args": ["serve"]
    }
  }
}
```
