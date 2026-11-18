---
name: toy-model
description: Answer "does this mechanism work at all" with a throwaway minimal simulation before any sweep is designed — the fewest neurons, dimensions and steps that can show the effect or its absence, one script, one figure, an answer in one session. The research version of Matt Pocock's prototype.
disable-model-invocation: true
---

# Toy model

A toy model is **throwaway code that answers one question** about a mechanism: can a low-rank net hold four attractors
with this nonlinearity, does this input push the state across a boundary, does this loss move the readout where we want.
The question decides the shape.

1. **State the question and the answer that would kill the idea**, in two lines, before writing code. If the answer
   would not change what is planned next, stop: the toy is not needed.
2. **Smallest that can answer.** Hand-set or few-step-trained weights, the fewest units and dimensions, no
   curriculum, no sweep, on the device the project uses for probes. Use the project's model code where it exists (one import), never a
   re-implementation that could disagree with it.
3. **Throwaway from the start, and marked so.** One script in `scratchpad/toy_<what>.py` (or the project's scratch
   folder), runnable with one command, no options. No tests, no error handling beyond running.
4. **Show the state.** Print the numbers that answer the question (fixed points, latent values, performance) and make one figure
   (making-figures conventions, colorblind-safe), sent to the user (showing-figures).
5. **Capture the answer, not the code.** The verdict goes in the verdict log as a short card marked `toy` (question,
   answer, the figure, the script's path and commit); a validated mechanism becomes a ticket or a plan, built properly.
   The script is committed once, then deleted or moved to scratch (organizing-projects).

A toy that works does not show the trained nets use the mechanism; say so in its card.
