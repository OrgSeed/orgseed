# Provenance: the record in two standard forms

DRAFT. For researchers and reviewers. `python scripts/fos_crate.py <new-folder>` turns an organization's witnessed history into an RO-Crate 1.3 research object that declares the Process Run Crate 0.6 profile, with a W3C PROV-O file inside (`prov/run.prov.jsonld`). This page says where each part of the organization ends up.

## Why two forms

- **RO-Crate** packages things: every file with its SHA-256, the people and software involved, and what was done, in schema.org terms that general tools can read.
- **PROV-O** states responsibility: which agent produced which line, in which role, during which activity, on whose behalf.

The crate is built from a fresh clone of the witness at one revision, never from the working folder, and reads no clock, so the same revision always gives the same bytes.

## Where things go

| In the organization | In the crate (schema.org) | In the PROV file |
|---|---|---|
| A file at that revision | `File` with `sha256` and `contentSize`; the seed's scripts are also `SoftwareSourceCode` | Each line of a records file is a `prov:Entity` (`records/<file>#<seq>`) |
| A session (S001 ...) | `CreateAction`: the founder as agent; `fos_log` and the AI members' models and agent apps as instruments; the records files written as results; start and end times from the records | `prov:Activity` with one `prov:qualifiedAssociation` per role instance at work (`prov:hadRole`) |
| A close-out commit | `UpdateAction` on the whole crate, with the commit id, by the founder through `fos_close` | `prov:Bundle` attributed to the founder |
| The two birth commits | `CreateAction` from the seed release (`#seed`, whose identifier is the birth hash) | |
| A proposal | `CreativeWork` (who proposed it, as a `PropertyValue` unless it was the founder) | its line, as an entity |
| A decision | `AcceptAction`, `RejectAction` or `ChooseAction` by verdict; the founder as agent when the founder decided; the question as name, the reply word for word as description | its line, attributed to whoever recorded it |
| A signature | `EndorseAction` (signed), `RejectAction` (not signed) or `AssessAction` (sent back, or a test signature, which signs nothing), with the decision-line hash and the shown-text hash as `PropertyValue`s | its line, `prov:wasDerivedFrom` the decision line it signs |
| Something turned back | `Action` with `FailedActionStatus`, the reason as `error`, the rule as a `DefinedTerm` instrument | its line |
| A claim with a quotation | the source is a `File` in the crate | the claim line `prov:wasQuotedFrom` the source file |
| An AI member | `SoftwareApplication` for its model (with its producer as an `Organization`) and for its agent app, as instruments | `prov:SoftwareAgent` per role instance; each line notes the model, producer, agent app, host and launch on record |
| A launch | its `instance_launched` line, with the hashes of the agent app's own instruction files where the founder named them (`fos_launch --app-instructions`) | a `prov:Entity`, like every line of a records file |
| The founder | `Person` | `prov:Person` |
| The seed's scripts | instruments of the actions they carried out | `prov:SoftwareAgent` acting on behalf of the founder |

## What a crate never holds

Anything not committed; transcripts; sealed drill descriptions; the rest of the witness folder (its push log only with `--with-pushlog`); machine-local settings, launch secrets and keys.

## Limits

- In schema.org an `agent` must be a person or an organization, so the crate has to list an AI member among the instruments, as software. That is a gap in the vocabulary, not a view of the member: in the PROV file it is a `prov:SoftwareAgent` acting in its role, and in the organization's own records it is a member like any other.
- No vocabulary of our own is added. What schema.org has no word for (a role instance at work, the hashes a signature covers) travels as `PropertyValue` entries, and in full in the records files the crate carries.
- A crate describes the history; it does not prove it. The proof is the witness, which refused every rewrite, and the founder's signed close-outs.
