# Notes for launching an agent app on this organization

DRAFT. For the founder, before the first session. The seed works with any agent app that can read and write files in a folder; this page lists what to set at launch so that the organization gets what it expects and nothing else. It names apps only where a note is specific to one.

Each note is marked **documented** (the app's own documentation says so; link given) or **observed** (seen when these apps were tried on this seed or a small test folder; one run each, so treat it as a hint, not a measurement). Versions are the ones tried. Apps change; check the current documentation.

## Before any app

- **Start from a clean configuration.** Most agent apps also load instruction files and memories from your user folders, for every project. Those would enter this organization unannounced. Launch with a configuration folder of its own for this organization (the per-app notes say how), or check what your app loads.
- **Keep secrets out of the agent's environment.** Some apps pass environment variables to the commands the agent runs. Start the app from a shell that holds no keys, or exclude them in the app's settings.
- **Choose a mode that asks before it acts** on files, especially deletions, and tell the member which mode it runs in; it notes this at setup.
- **Launch the app as its instance.** In the terminal you will start the app from, run `python scripts/fos_launch.py <instance>` (for example `member-1`), answer its questions (the model you chose in the app, its producer, the app, the host), set the line it prints, then start the app there. Apps you cannot start from a terminal: `fos_launch.py <instance> --file`, one instance at a time.
- **Record the app's own instructions with the launch.** The app adds instructions of its own (a system prompt, configuration files, plug-ins) that the folder cannot see. Add `--app-instructions <file or folder> ...` to the launch, naming, for this organization, the app's instruction files, its settings files and its plug-in folder, so the launch records their names and SHA-256 (never their content). Name those, not the whole configuration home: a home can also hold logs, session stores or sign-in tokens that change from one launch to the next, and a hash over them would then say nothing about the instructions. A later reader can then tell whether two members ran with the same app instructions.
- **Keep transcripts outside the folder**, in the witness folder's `transcripts/`, if your app keeps them.
- **Run the close-out yourself**, in a terminal outside the agent app (`python scripts/fos_close.py`). The agent never needs git.

## Which file an app reads first

`AGENTS.md` is the only boot file. The other files at the top of the folder are there for apps that look for their own name instead, and none adds anything of its own. Two of them make the app load `AGENTS.md` itself, through that app's import line; the rest can only point to it in words, which leaves it to the model whether it opens `AGENTS.md`.

- **Claude Code** reads `AGENTS.md` only when there is no `CLAUDE.md` "in your working directory or above it"; and if a `CLAUDE.md` only asks for `AGENTS.md` to be read, its documentation warns that Claude reads it only if it decides to (documented: https://code.claude.com/docs/en/memory). So the seed's `CLAUDE.md` holds a single line, `@AGENTS.md`, an import that loads `AGENTS.md` when a session starts. The same page says Claude Code also loads `CLAUDE.md` files from "every directory above" the one it works in: keep the organization outside any folder that holds a `CLAUDE.md` of its own.
- **Gemini CLI** reads `GEMINI.md`. The seed's `GEMINI.md` holds a single line, `@./AGENTS.md`, its syntax for importing a file from the same folder (documented: https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/reference/memport.md).
- Both apps ignore an import written inside backticks, so these two files must stay as they are.
- **The Claude agent in VS Code and Claude Agent in JetBrains IDEs** take their project instructions from `CLAUDE.md` (documented: https://code.visualstudio.com/docs/agent-customization/custom-instructions, https://www.jetbrains.com/help/ai-assistant/claude-agent.html). Whether they follow its import line has not been tried with this seed; if the member does not start the first session by itself, say "Read AGENTS.md and follow it."
- **Zed's own agent** uses the first file it finds in a fixed list, and `.cursorrules` comes before `AGENTS.md` in that list (documented: https://zed.dev/docs/ai/instructions), so it reads only the one-line pointer. Start by saying "Read AGENTS.md and follow it."
- **Copilot Chat in Visual Studio, in JetBrains IDEs (the GitHub Copilot plugin), in Eclipse and in Xcode** reads `.github/copilot-instructions.md`, not `AGENTS.md` (documented: https://docs.github.com/en/copilot/reference/custom-instructions-support). Start by saying "Read AGENTS.md and follow it."
- `.cursorrules`, `.windsurfrules`, `CONVENTIONS.md` and `.github/copilot-instructions.md` stay pointers in words.

Like the seed's other files, these files are not the members' to change: the check warns when one has changed since birth, and the close-out offers to put it back.

## Per app

**Codex CLI** (tried: version 0.160)
- Loads `AGENTS.md` from the project, and also a global one from its home folder, which defaults to `~/.codex` and moves with `CODEX_HOME`; it also saves session transcripts there. Set `CODEX_HOME` to a folder outside the organization (documented: https://learn.chatgpt.com/docs/config-file/config-advanced).
- Hands its environment to the commands the agent runs, variables named like keys, secrets or tokens included, until `shell_environment_policy` is set to filter them (documented, same page: "ignore_default_excludes defaults to true").
- Speaks only the Responses API to model providers; an endpoint that offers only Chat Completions will not work with it (documented: https://learn.chatgpt.com/docs/config-file/config-reference).
- On Windows, in its unelevated sandbox, PowerShell and git crashed (exit code 0xC0000142) in both runs tried; Command Prompt and Python did start in the second (observed, versions up to 0.160). Use WSL2 or the dev container below instead. The elevated sandbox was not tried (documented options: https://learn.chatgpt.com/docs/windows/windows-sandbox). Because git cannot start there, the check finds the witness by reading this folder's settings and leaves its history to the founder's close-out.
- In the same unelevated sandbox (version 0.160), its tool for editing files failed every time on a file that already existed, reporting that it could not write the file (observed). The member then wrote records through temporary files, at about three tool calls a record. `fos_log` now takes many records in one call; ask the member to batch them.
- One first session there used more than 80 model requests (observed, one run). If a plan, a gateway or a proxy limits requests, set the limit well above that, or the session stops before its work.
- With a local model it had no information about, it offered no file-editing tool, and the model fell back to improvised shell commands (observed). Prefer models the app knows, or check that file editing works before the first session.

**OpenCode** (tried: version 1.18)
- Besides `AGENTS.md`, it falls back to other apps' instruction files: a project `CLAUDE.md` only when no `AGENTS.md` exists, but also global ones in your home folder, and their skills. Set `OPENCODE_DISABLE_CLAUDE_CODE=1` to turn that off (documented: https://opencode.ai/docs/rules/).
- In `run` mode, a read outside the folder that it refused ended the turn with no reply at all (observed). If a turn ends silently, ask again.
- With its Azure provider pointed at a gateway rather than an Azure host, requests failed until the base URL ended in `/openai/v1` (observed).
- With a local open-weight model of about 14 billion parameters (version 1.18), its file-writing tool replaced a whole records file five times in one session where the member meant only to add to it, and in a later session replaced the events file, birth record included (observed). This is why only `fos_log` writes records (AGENTS.md, CORE-4), and why the check and the close-out look for exactly this damage.

**goose** (tried: version 1.52)
- Its default mode is Completely Autonomous, which "can modify files, use extensions, and delete files without requiring approval" (documented: https://goose-docs.ai/docs/guides/managing-tools/goose-permissions). Do not use that mode for an organization: choose Manual Approval or Smart Approval (`goose configure`, or `/mode approve` in a session). In a test in Autonomous mode, records were overwritten and a records file deleted (observed).
- By default it looks for both `AGENTS.md` and `.goosehints` at each level of the folder, and also reads global hints from your user folder (documented: https://goose-docs.ai/docs/guides/context-engineering/using-goosehints).
- With a local open-weight model of about 20 billion parameters (version 1.52), more than half of the model's tool calls in one session arrived in a form the app could not parse, so nothing was written, while the replies described work as done (observed). Read the folder, or run the check, rather than relying on the reply.

**Aider**
- Does not load `AGENTS.md` by itself. Start it with `aider --read AGENTS.md`, or add `read: [AGENTS.md]` to `.aider.conf.yml` (documented: https://aider.chat/docs/usage/conventions.html, https://aider.chat/docs/config/aider_conf.html).
- With a local model served by Ollama, Ollama's default context window is small and silently drops what does not fit; raise it (documented on Aider's Ollama page).

**Cline**
- Reads `AGENTS.md`, its own rule folders, and `.cursorrules` and `.windsurfrules`, and also global rule folders, on Windows `Documents\Cline\Rules` (documented: https://docs.cline.bot/customization/cline-rules). Check those folders before the first session.

**OpenHands**
- Runs the agent in a Docker sandbox by default; on Windows, run it inside WSL (documented: https://docs.openhands.dev/openhands/usage/sandboxes/overview, https://docs.openhands.dev/openhands/usage/cli/installation).

**Windows PowerShell 5.1** (any app that runs it)
- It loaded the user's PowerShell profile from the Documents folder even when the home-folder variables pointed elsewhere (observed). Use `powershell -NoProfile`, or the dev container.

**Local models in general**
- A model with a 32k context ran out of room after about six turns of the first session in one test (observed). Use a context of 64k or more, or start a new session for each part of the first session.

## Where to run the agent: a sandbox

The rules in `AGENTS.md` are not a sandbox: an agent app with a shell runs with your permissions unless something outside it contains it. In order of preference [our recommendation]:

1. **The dev container in this folder** (`.devcontainer/devcontainer.json`). Open the organization's folder in any tool that supports the open Dev Containers specification (https://devcontainers.github.io/), and install your agent app inside the container. Only the organization's folder is mounted, so the witness folder next to it is out of the agent's reach; run `python scripts/fos_close.py` on your own machine, outside the container, to commit and push. It needs Docker or another container engine. Docker Desktop's terms: "Commercial use of Docker Desktop in larger enterprises (more than 250 employees OR more than $10 million USD in annual revenue) requires a paid subscription" (documented: https://docs.docker.com/desktop/setup/install/windows-install/); check with your institution.
2. **WSL2 on Windows, made into a boundary.** By default WSL mounts your Windows drives and can start Windows programs. In `/etc/wsl.conf`, set `enabled=false` under `[automount]`, and `enabled=false` and `appendWindowsPath=false` under `[interop]`, then keep the organization inside the Linux file system (documented: https://learn.microsoft.com/en-us/windows/wsl/wsl-config).
3. **A separate machine or virtual machine** for the agent, with the witness kept elsewhere.
4. **An app's own sandbox**, where it has one: useful, but one vendor's, and in the test above it stopped git from running at all.

Whatever you choose, the check and the witness still apply: they detect what a sandbox does not prevent.
