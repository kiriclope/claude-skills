---
name: publishing-drafts
description: Publish and keep current the pages readers use — manuscript drafts, figure pages, notes — as claude.ai Artifacts (or a Google Doc when asked), with the page source and its builder kept in the repo, the live page read and merged before every republish, the same URL kept so shared links stay valid, and every reader comment collected and answered. Use when asked to publish, share, update or republish a draft, figure page or notes page, at the start of a session on a project that has published pages, or after any edit that changes a published page. Not for local-only figure viewing → use the project's figure gallery; not for writing the text → use writing-paper.
---

# Publishing drafts

A published page is only useful while it is current, recoverable and read back. Pages have been lost
because their builder lived in a temporary session folder; readers kept reading a stale pinned version;
a retired page with the same title kept being shared; and a page's comment threads went unread for
days. Every rule below prevents one of those.

**Publish only when the user asks for a shareable or off-machine page.** Some projects keep figures in
a local gallery by default — check the project's notes before publishing anything.

## Step 0 — the ledger (start of every session that touches a published page)

The project's pages are recorded in `.claude/project.yaml`:

```yaml
pages:
  - name: Draft                         # unique; the title readers see
    url: https://claude.ai/code/artifact/<id>
    source: paper/build/draft.html      # the built page (may be gitignored; never in a temp or job folder)
    builder: build_draft.py             # tracked script that rebuilds it from repo files
    inputs: [docs/paper/*.md]           # optional: what the page is built from
    shared: private                     # private | link
```

```bash
python <this skill>/scripts/pages_check.py      # temp-folder sources, missing builders, stale pages, size, duplicates
```

Fix every `error` before publishing. A page without a ledger entry gets one now.

## Step 1 — read the comments (start of session, and after every publish)

For each page in the ledger, read its comment threads with the **ArtifactComments** tool (load it with
ToolSearch if it is deferred). For each thread: apply the requested change, or answer it, or ask the
user — never leave a thread unread. Report "N threads: a applied, b answered, c need you" in one line.
Threads are only answerable when they were sent to Claude; if readers comment without that, tell the
user so they send the thread to Claude.

## Step 2 — build from the repo

- The page is produced by the tracked `builder` from repo files (Markdown → HTML, figure embeds,
  captions). Never hand-edit the built page; change the inputs and rebuild.
- Before publishing, grep the built page for stale content: old figure numbers, renamed terms,
  placeholders, working notes not meant for readers.
- Keep the page under 16 MB including embedded images: resize and quantize the web copies, and keep
  full-resolution files in the repo for download.

## Step 3 — publish to the same URL

1. **Read before you write.** If this session has not published the page yet, run the Artifact tool's
   `read` action on its `url` first. If the live page has edits the repo source does not (another
   session, an in-page edit), merge them into the inputs and rebuild — never publish over them. If the
   repo source is missing, recover it from the saved copy the read reports and save it at `source`.
2. Publish with the `url` from the ledger (and the same file path within a session) so the link stays
   the same; give the version a short `label` ("v12 results pass"). Never use `force` unless the user
   explicitly says to discard the newer version.
3. **Shared by link?** The read header says when link-holders see a pinned earlier version. Republishing
   does not move that pin, and no tool can: tell the user to advance it from the page's share menu.
4. **Replacing a page with a new one** (new file path → new URL): retitle the old page at once
   ("OLD … (retired)", with a pointer to the new link) so two pages never share a title, and update
   every cross-link and the ledger.

## Step 4 — update the ledger

Record the url, source, builder and sharing state in `pages:`; commit the builder and the ledger with
the work (log-and-ship). Then read the comments again (Step 1).

## Text documents for collaboration

For an editable, commentable text document rather than a built page, run the Artifact tool's
`quickstart` (intent `document`) to see which document types the account offers; use a Google Doc
only when the user asks for one.

## Never

- Leave a page's source or builder only in a temporary, job or scratch folder.
- Publish without reading a live page this session has not published, or over edits you did not merge.
- Give a new page the title of an old one, or delete a page without the user's explicit request.

One line in the reply: pages published (url, label), comment threads handled, ledger updated.
