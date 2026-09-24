---
name: deepen-plan
description: Enhance the current feature plan with focused research on uncertain sections. Use after /sp:03-plan for complex features, before /sp:04-red-team.
---

## User Input

```text
$ARGUMENTS
```

## When to Use

- After `/sp:03-plan` for complex features that have "NEEDS CLARIFICATION" sections
- Before `/sp:04-red-team` to strengthen the plan with concrete details
- When the plan has high-uncertainty areas that need research

## Execution

Launch the `deepen-plan-loop` agent using the Agent tool. Pass the user input above as the agent's prompt so it can consider any user-specified focus areas.

The agent will:

1. Scan plan.md for uncertainty markers (NEEDS CLARIFICATION, TBD, TODO, vague language)
2. Research and expand each uncertain section
3. Commit after each pass
4. Repeat up to 3 times, stopping when all uncertainties are resolved or progress stalls
5. Report cumulative results

Report the agent's results to the user when it completes.
