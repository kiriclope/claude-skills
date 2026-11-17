---
name: showing-figures
description: Put a figure in front of Leon, not just in front of Claude — choose between sending the file (SendUserFile, works on any device), opening it full size in an X window (`show`, needs a live ssh -X display) and the browser gallery (many figures), convert PDFs to PNG first, and say which way it went. Use whenever a figure, plot, PNG or PDF should be seen by the user: a verdict's figure, "show me", "let me see it", "display the figure", "open it", after building or fixing a figure. Not for publishing a set of figures to localhost:8000 → figure-gallery; for making the figure → making-figures.
---

# Showing figures

Reading an image with the Read tool shows it to Claude only. A path in the chat, or an image
printed in the terminal (chafa, sixel), is not shown to the user either: tool output goes to Claude.
A figure counts as shown only after one of the routes below succeeded.

## The route (first that fits)

1. **Send it — the default.** `SendUserFile` with the PNG. It reaches the user on any device
   (terminal, phone, Remote Control) and stays in the conversation. Send the figure first, then the
   text that discusses it (auditing-results §0: figure first, verdict right below).
   A session without the `SendUserFile` tool (a plain terminal session) starts at route 2.
2. **Full size on the desk** — when the user asks to open or zoom, or the figure is too dense for the
   chat view: `show <file> [more…]` (`scripts/show`, linked as `~/.local/bin/show`). It opens X
   windows on the ssh -X display (close with q). It exits 1 when no display answers — a background
   session often keeps a dead `DISPLAY` from a closed ssh: then send the file and say "the X display is
   not reachable; reconnect with ssh -X for full size".
3. **Many figures, or to browse later** (a sweep's figures, before/after sets): figure-gallery
   (localhost:8000), and send the one or two that carry the message.

## Rules

- **PDF → PNG first** for sending: `pdftoppm -r 150 -png -singlefile fig.pdf fig` (Leon cannot open
  PDFs). `show` opens PDFs directly.
- Look at the PNG yourself (Read) before showing it; never show a figure you have not checked.
- Say in one line how it was shown ("sent", "opened in X", "in the gallery under …"). Never write
  "see the figure" when it was not shown.
- Describe colors by name + shape when discussing it (Leon is colorblind).
