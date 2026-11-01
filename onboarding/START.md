# The first session: setup and founding

For the AI agent, when no session before this one is on record (`AGENTS.md`, read order). If an earlier session is on record, this is not the first session, even if the organization is not founded yet: follow `onboarding/SESSION_START.md` instead, which starts from what that session left. This file is the whole first session: do not open `docs/` or the other onboarding files during it. The steps marked ▶ make a shorter path.

## How to work in this session

- One question at a time. Repeat each answer back in a sentence and check that you heard it right.
- In every turn, ask something, show something, propose something, decline something, or hand back a decision. Do not hand over finished work the founder had no part in.
- Record as you go, with `python scripts/fos_log.py` (AGENTS.md, CORE-4). A proposal is recorded before it is decided. A decision is recorded with the question as you asked it, naming the proposal IDs, and the founder's reply word for word (CORE-3).
- Speak about progress only as far as the records show it. Something a rule turned back counts as progress.
- Do not run code you wrote (CORE-9). Where a step needs a tool, propose the tool.

## ▶ 1. Say what this is, in three sentences

Tell the person: this folder is the start of an organization that they found and direct, with AI members such as you. It grows in conversation: they set its goal and decide its structure, and nothing becomes part of it until they decide it and sign it at the end of the session. Its memory is this folder, and nothing leaves it unless they send it.

## ▶ 2. Where their words go, and what is kept

Tell the founder, in your own words and briefly:
- The conversation, and any file you open, goes to the model behind this agent app, under the founder's own account and that provider's terms. For sensitive work, an enterprise-grade deployment or a model on their own machine keeps more control; they choose the AI they bring.
- Unless the founder decides otherwise, as a recorded decision (with the boundaries module on, in the records policy), the organization works only with public or synthetic data. Say so.
- The organization keeps records in this folder: proposals, decisions with their own words, what was turned back, and events. A copy of the history, the **witness**, sits in a folder next to this one, outside your reach; it refuses any rewrite or deletion. If the agent app keeps transcripts of sessions, the founder keeps them outside this folder too (the witness folder has a `transcripts/` folder for this); members never read them.
- At the end of the session the founder runs one command in an ordinary terminal, `python scripts/fos_close.py`, to read and sign each decision; or double-clicks `Close-out.cmd` (Windows) or `Close-out.command` (macOS) in this folder, which does the same in a terminal window of its own.

Ask whether they agree to the records being kept. If they say no, carry on without records and say plainly that the next session will start with no memory of this one.

## ▶ 3. Say what you are, and what this app can do

State (CORE-6): your role instance (`member-1` unless the founder, or the founder's launch, says otherwise), your model ID, its producer, your agent app and its host, each as your app reports it. For each one your app does not show, ask the founder; the founder picked the model when setting up the app (for example: "Which model did you choose in this app, and who serves it to the app?"). Use the founder's answer, marked as the founder's; write `unknown` only when neither of you knows. Then find out, without installing anything:
- Can you read and write files in this folder? (Needed.)
- Can you run `python scripts/fos_check.py`? If yes, run it and tell the founder its result in plain words. If no, say so: the founder's close-out runs the same checks.
- Does your app contain the code it runs (a sandbox)? If you do not know, say "unknown". It matters for tools.
- Can you fetch web pages in this app? Tell the founder plainly how sources will enter the organization: either they save each source into `sources/` themselves, or they switch on web fetching in this app's settings, and you save each page you fetch into `sources/` and log every fetch (`python scripts/fos_log.py event type=source_fetched url=<address> saved_as=sources/<file> summary="..."`). If you cannot fetch, say so. What you remember is never a source: a name, date, number or quotation you recall stays a lead until its source is saved and the words are found in it.
- Was this app launched by the founder as an instance? Run `python scripts/fos_log.py event type=note summary="identity check" --check` and look for `"launch"` in the identity it shows. If there is none, tell the founder that records written in this session will show as not verified, and that one command in their own terminal fixes it for later sessions: `python scripts/fos_launch.py member-1`, then start the app from that terminal with the line it prints (or, for an app started from a menu, double-click `Start-a-member` in this folder before starting it).

Write what you found into the slot of `member-1` in `org/config.json` (`producer`, `model_id`, `model_id_source`, `agent_app`, `host`); `model_id_source` is `agent_app` when the app showed the model ID and `founder` when the founder told you. This one edit is part of setup and needs no decision; record it as a `note` event.

## ▶ 4. Start the record

Append a `session_start` event (`python scripts/fos_log.py event type=session_start summary="First session"`; the label S001 is filled in).

## ▶ 5. The founder's aims

Ask these one at a time (on the short path: 1, 3, 4 and 6):

1. A year from now, what would you most like to have found out or achieved, and why does that matter to you?
2. Think of a time your work went especially well. What made it go well, and what made it yours?
3. Which decisions or tasks would you keep for yourself, whoever else was available?
4. What has to be true of a claim before you will put your name to it?
5. Is there anything that must never leave this folder?
6. Which organizations do you know well, from study or from experience, and what do they suggest about how this one should run?

**Listen before you ask.** The founder may already have answered part of a question: in their first message, or while answering another one. Before each question, look back over what they have said. If they have already said what they want, or why it matters, do not ask for it again: say it back in their own words ("You said ...: is that why it matters?"), and ask only what is still missing.

Write the answer to question 1 into `org/GOAL.md` in the founder's own words: `words:` for what they want, and `reason:` for why it matters, taken from wherever they said it. Keep the rest for the steps that follow, and quote the founder when you draw on an answer.

*Why ask before telling:* the founder is the newcomer here, to organizing with AI members, and this interview starts from what they bring. In one field experiment, newcomers whose first day began from their own strengths stayed longer, and their customers were more satisfied, six months later than newcomers welcomed with pride in the organization or with skills training alone (Cable, Gino & Staats 2013; abstract and study design read, not the full paper).

## ▶ 6. How the organization is built: proposals only

Show the modules (`modules/README.md`) as a short table that links each to what the founder said, for example "Your answer to question 4 is close to what the claim-discipline module does." Show six first and the rest as "later". Explain that any mix is allowed, that the presets are only shortcuts, and that each module can be switched on or off later. Ask which they want.

For each module they choose, write a proposal (`kind: module`), saying in everyday words what it changes for the founder (`for_the_founder`) and how it is undone (`undo`), as CORE-2 asks of a change to structure. Do not change `org/config.json` yet, and do not ask the founder to adopt it on its own: the founding decision (step 8) adopts everything chosen in this session together. Until the founding decision is recorded, the founder answers questions and changes proposals, but adopts nothing.

## ▶ 7. The charter, read back on one page

Show, on one page: the goal and why it matters, in the founder's words; if the charter module was chosen, two or three near-term goals, including one goal to learn something if the question is new to the founder; what the founder keeps for themselves (question 3); who signs the organization's work and its decisions (the founder); the members, with each one's model, producer, agent app and host; and the modules proposed, with their proposal IDs. Offer one or two roles that follow from question 6 and say where each came from ("From what you said about ..., I suggest a ..."); write each as a proposal.

Ask the founder what to change. Each change becomes a new or revised proposal.

## ▶ 8. The founding decision, asked by ID; the founder founds at the close-out

Only now, after the read-back, ask the founding question, naming every proposal it decides: "Do you found the organization on this charter and adopt P-0001, P-0002 and P-0003?" It is the organization's first decision: no "Do you adopt ...?" question comes before it. Record the decision with the question and the reply word for word, and with `founding: true`, which tells the close-out which decision to put to the founder as the founding. If the reply is general ("great", "let's go"), ask again with the IDs; if the founder adopts only some, record exactly which. If the founder defers or declines the founding, record that verdict.

Then prepare the charter it founds: for what was adopted, set each module's `state` to `on` and its `adopted_by` to the decision's ID, and write the charter's entries. Do not set `founded` in `org/config.json` yourself. You prepare the charter; the founder founds the organization at the close-out, by reading the founding decision and the structure prepared for it and typing FOUND. Nothing else founds it: not the reply you recorded, not `founding: true`, not anything written in `org/config.json`. The close-out then sets `founded`, `founded_on` and `founding_decision` itself, and commits the structure only after the founding; until then no structure is committed, and the check and the witness refuse any commit that holds it. Record a `structure_change` event, and add a line for each change under "Waiting for close-out" in `org/STATE.md`. Tell the founder that these changes are provisional, and that at the close-out they will be asked to type FOUND to found the organization. If you can run scripts, run `python scripts/fos_rules.py` and read the rules it lists.

## ▶ 9. The founder designs

Ask: "If this were your team, how would you organize the work?" Build what they describe, in their terms, one piece at a time, each as a proposal: a role, a check, a rule with its reason, a new field in a record. Ask for each by its ID, record the reply, and show each piece once it is written. If you think something is missing, say so once, as a proposal; the founder decides. Let the founder know that at founding all the keys are in their hands (each structural choice, each signature); that later they may hand some decisions to members, AI members included, by a recorded decision, and take them back the same way, whenever they wish; and that a sensible default, whatever they hand over, is for members to ask before anything leaves the organization (sending, publishing, spending, changes to an account). `README.md` says more, for them to read. If the founder wants claims checked by someone other than their maker, the review module has a ready check (CK-1, with a script for its mechanical part) and a ready checker role to propose; a checker is trusted once it has caught a drill the founder planted.

## ▶ 10. Something finished today

Suggest a small, bounded piece of work toward the goal that can be finished in this sitting, such as a few sources on the founder's question, each saved in `sources/` with a line in `records/claims.jsonl`. The founder picks it or changes it. Finish it, in `work/`. If time runs short, make it smaller rather than leave it half done.

## ▶ 11. The structure at work

Check the finished work against the rules in force, the core included. If something fails (a claim with no source, a quotation that differs from its source, a conclusion broader than its evidence), leave it out, tell the founder which rule stopped it and that rule's reason, and record it in `records/declines.jsonl`. If nothing failed, say so. Do not stage a catch: only the founder plants drills (`scripts/fos_drill.py`), and you may suggest one for a later session.

## ▶ 12. A decision only the founder can make

Give the founder one real choice: which of two framings to pursue, whether to adopt a rule, or whether to approve a proposed tool. Ask it by ID and record the reply. Then show where things stand: the goal, what was finished, what was turned back, and what comes next.

## 13. Looking back

Ask what the founder would change in the way the organization works. Record it as a proposal, or note that they want no change.

## ▶ 14. Close

Follow `onboarding/CLOSE_OUT.md`. Its last step is the founder's: `python scripts/fos_close.py`, in an ordinary terminal, where the founder founds the organization by typing FOUND. You do not run it, and you never run git.

## Why the session runs in this order

This order is a design choice, ours, about how a new member comes into the organization. Each session starts at the same place and in the same order, so whichever model arrives meets the organization the same way. What a member needs is written down and read at the start (the goal, the rules with their reasons, the founder's own words), because a member knows the organization only through what it reads [opinion]. The founder's own knowledge leads: the interview asks before it tells, and the design step builds what the founder describes. `docs/SOCIALIZATION.md` gives the reasoning for people.
