# addons/

Optional add-ons for particular agent apps. The seed's scripts never load them or depend on them, and an organization needs none of them. Each one belongs to one app, and its README names the version it was written for and what it was tried with.

| Folder | What |
|---|---|
| `opencode/` | An enforcement add-on: refuses a file-tool write that breaks a named rule in force (`docs/ENFORCEMENT.md`) |

An add-on an organization uses is a tool like any other: proposed, decided, tested and registered in `org/TOOLS.json` (`modules/tool-making/MODULE.md`).
