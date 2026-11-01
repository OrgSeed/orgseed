# Close-out (every session)

Two parts: what the AI member does, then what the founder does. If time is short, do steps 1, 4, 6 and 7 at least.

## The member's part

1. **Sum up for the founder in four short parts:** the decisions they made (quoted, with IDs); the work done; the next steps; and the decisions you need from them, numbered, the weightiest first.
2. **Promises.** Name future work only if it has a line in `records/commitments.jsonl` with an owner and a trigger (memory module). If you cannot give it one, do not promise it.
3. **Look back.** If it has not been done this session, invite the founder to say what should work differently. Record a proposal, or note that they want no change. A member's own ideas for change are welcome as well: record them as proposals beside the founder's, to be talked over with the founder, now or at the next session, before any decision on them.
4. **State and letter.** Rewrite `org/STATE.md` with the current state only, keeping its "Waiting for close-out" list: one line per structural change made since the last close-out, with proposal and decision IDs. Write `org/LETTER_TO_NEXT_SESSION.md` for a reader who remembers nothing: decided, done, open, warnings. The next member reads it before anything else. If the founding decision has not been taken yet, say so at the top of the letter, with the step of `onboarding/START.md` where the session stopped and what the founder has already answered. Note any role the roll-call found stale and what the founder decided about it.
5. **Roles.** Run the roles whose trigger is `close_out`, and make sure each role that ran this session has a record.
6. **Log.** Append a `session_end` event.
7. **Hand over to the founder.** Ask the founder to run, in an ordinary terminal opened in this folder:

   `python scripts/fos_close.py`

   or to double-click `Close-out.cmd` (Windows) or `Close-out.command` (macOS) in this folder, which opens a terminal window and runs the same script. Tell them what it will do: check the records, offer to restore anything deleted or rewritten, and, while the organization is not founded, ask them first whether to found it on the charter you prepared, which they do by typing FOUND; then show each decision of this session with the question as asked and their recorded words, and ask them to sign each one or not; then commit and push to the witness. Do not run it yourself, and never run git (CORE-5). If they cannot run it now, say plainly that this session's decisions stay unsigned and its changes uncommitted, and that the list in `org/STATE.md` keeps them for the next close-out.

## The founder's part

`python scripts/fos_close.py` is yours, and it needs no AI. It shows what fails first, every item numbered; if anything fails, you type the number of failing items before it lets you sign anything. If the organization is not founded yet, the founding comes next, on its own: the founding decision as the member recorded it, and the structure prepared for it, with every change from the organization's birth in words. Each change says whether the founding adopts it, whether the close-out offers to put it back after the founding, or that it cannot be put back here; if you do not want one of those, answer n, or b with a note. To found the organization on it, type FOUND, in capitals; n leaves it unfounded. Nothing else founds it, and until it is founded no structure is committed: the structural files stay changed in the folder, and the commit says so. Then it shows each decision. Read each before you answer: sign (`y`) only what you decided; `n` leaves it a proposal. The signature is what makes a decision final, because you, not the software, answer for what the organization decides. Then you choose what the commit holds: structure nobody signed can be put back, and changes to the seed's own files, or files outside the organization's folders, can be put back or left out.

Without git on your machine, the close-out keeps a dated copy of `records/` in the witness folder instead of a commit. In Git Bash on Windows, run it as `winpty python scripts/fos_close.py`, or use PowerShell or Command Prompt.
