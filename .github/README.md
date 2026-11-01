# OrgSeed

**A seed for a human–AI organization.** A folder of plain files that you grow into an organization of your own: you, and AI members, working toward a goal you set. Members propose; you decide. Use it to do your research with AI members, or to study human–AI organizing itself.

The seed itself is nothing to install: no server, no account. It sends nothing anywhere.

## This repository

This is the version of the seed the pilot ran: OrgSeed v1.3.2, the seed commit `44a3809` that the pilot's frozen plan names. It is identical to that tagged commit apart from its licence text (`LICENSE`, `LICENSE-docs`, `NOTICE`, the Licence section of the root `README.md` and one licence line in `docs/DESIGN_NOTES.md`) and this page. It is free for research and other noncommercial use. Editors or scholars who want a later version can ask through the journal's editorial office.

The pilot's plan, code and scoring data are in [`OrgSeed/orgseed-pilot`](https://github.com/OrgSeed/orgseed-pilot). That repository does not hold the seed.

## The words on this page

- **You** are the scholar who founds the organization and decides for it; the seed calls you the founder.
- An **AI model** is trained by a company, its **producer**.
- An **agent app** is the program through which a model reads and writes files on your computer and runs commands. The app is not the model; the model works through it.
- A **member** is a participant in your organization, you included. A model becomes an AI member when it reads the organization's rules and joins. Until then it is the AI model, working through your agent app.
- The **witness** is a second folder that keeps the organization's history safe (below).

## What you need

- **An agent app that can work in a folder on your computer.** Any capable one, desktop or terminal. One open-source option is [OpenCode](https://opencode.ai); our pilot used OpenCode 1.18.34. You choose the model it runs.
- **Python 3.** The seed's few scripts, and the launchers below, need it before any AI is involved. If you are not sure you have it, you can ask the AI model, working through your agent app, to check and install it for you; or install it yourself (on Windows, from the Microsoft Store).
- **Git** (recommended). With Git the witness keeps the full history; without it, dated copies of the records.

## Make the folders, then found the organization

Founding is not one click. It is the first session, a long conversation in which you set the goal and the structure, and it ends with one word typed by you. The steps before it only make folders.

1. **Download this repository** (green "Code" button, then "Download ZIP") and unzip it. This folder is the seed; leave it as it is.
2. **Double-click `Found-an-organization`** (`.cmd` on Windows, `.command` on a Mac) in the seed's folder. A small window asks for a short name; type one and press Enter. Despite the launcher's name, nothing is founded yet. It copies the seed into two folders next to it:
   - your organization, under the name you gave;
   - its **witness**, with `-witness` at the end of the name: a copy of the organization's history that refuses any rewrite or deletion, kept outside the folder the AI members work in. It is why the record can be trusted later. You never need to open it.

   No AI is involved in this step.
3. **Open your organization's folder in your agent app and say: "Read `AGENTS.md` and follow it."** `AGENTS.md` holds the organization's rules, each with its reason. The AI model, working through your app, reads it and joins as the organization's first AI member. (Before you open the app, you may double-click `Start-a-member` in the organization's folder; it writes down which member is starting, on which model, so the records can be traced to it. The seed recommends it; nothing stops without it.)
4. **The AI member runs the first session with you.** It tells you where your words go, asks about your goal and how you think the work should be organized, proposes a structure, reads a charter back to you, finishes one small piece of work, shows you something a rule turned back, and hands a decision back to you, recording your words as you say them. It can take a long sitting, or more than one: if you stop, the next session picks up where this one left off. This conversation is the founding.
5. **At the end, double-click `Close-out` in your organization's folder.** A window opens that no AI controls. It checks the records; asks whether you found the organization on the charter the member prepared, which you do by typing FOUND; shows you each decision the member recorded, in your own words, and asks you to sign it or not; then saves the session to the witness. Nothing becomes part of your organization until you sign it, and the organization exists only once you have typed FOUND.

## Why the two small windows

An AI member can write files. So the steps that make things final happen in windows the members do not control: making the organization and its witness, founding it, and signing decisions. Only you can found the organization, and only you can sign.

## What stays yours

At the founding every decision is yours: the structure, every change to it, and every signature. Members, AI members among them, propose; you decide. Later, if you choose, you can hand some decisions to members, by a recorded decision of your own that you can narrow or take back at any time.

By default, members ask you before anything leaves the organization: before anything is sent, published or uploaded, before money is spent, and before any change to an account.

## Privacy

- **The seed sends nothing.** Its own scripts never connect to the internet; they only read and write your folders.
- **Your agent app does send data.** It sends your conversation, and any file the AI member opens, to the company that serves the model, under your account and that company's terms. Choose the app and the model as you would any service; `docs/DATA_FLOW.md` says more.

## For researchers

- **Watch:** open `view/org_view.html` in a browser to see an organization drawn from its files.
- **Read the record:** `records/` holds the history, which can only be added to; `docs/PROVENANCE.md` describes its export in two open provenance standards (W3C PROV and RO-Crate).
- **Run it safely:** `docs/HARNESS_NOTES.md` covers the settings that keep your own files and secrets away from the member, and a dev container.
- **Each module states its theory, or says it claims none:** `modules/`.

## Licence

Free for research and other noncommercial use. Code and machine-read files: PolyForm Noncommercial License 1.0.0 (`LICENSE`). Documents: CC BY-NC 4.0 (`LICENSE-docs`).
