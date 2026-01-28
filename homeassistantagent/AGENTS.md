## Agent Instructions
- This add-on targets Home Assistant; consider ingress support in design decisions (favor UI access via ingress).
- When adding a new Python file, confirm the Docker build copies it into the image.

If you need to use the Home Assistant websocket client refer to the /docs/ha_ws_readme.md

When you read a file if you see a comment near the top "## DOCS: somefile.md" you can optionally read that md file to understand more about the purpose of the functions within the files.
Typically we will use this for tool specs.

Conversely if the user has given you a tool spec and asked you to implement or modify the tool, please ensure that this reference is included near the top.