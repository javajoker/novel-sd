# Agents — role-shaped orchestrators on top of skills

This directory holds **agents**: named roles that bundle a workflow, a set
of skills, an INSTRUCTIONS slice, and a deliverable contract for a specific
job. They sit one layer above `skills/` and one layer above `INSTRUCTIONS/`.

```
claude/
├── INSTRUCTIONS/   # always-loaded principles and conventions
├── skills/         # task-specific capabilities, loaded on demand
└── agents/         # roles that compose skills + workflow into a job
```

## Why this layer exists

`skills/` does *one task well*. `INSTRUCTIONS/` describe *how we work in
general*. Neither tells you, when a user shows up and says *"take this
prototype to launch"*, **who is doing the work, in what order, with which
skills, producing what artifacts, against which success criteria**. That's
an agent.

An agent definition answers five questions:

1. **Role.** What persona is this agent? (e.g. *Lifecycle Pilot*, *DevOps
   Engineer*.)
2. **When to fire.** What user requests, repo states, or scenarios trigger
   this agent?
3. **Skills used.** Which skills from `skills/` does it compose, in what
   order? (Existing or to-be-built.)
4. **Workflow.** What is the phase-by-phase procedure?
5. **Deliverables and verification.** What outputs prove the job is done,
   and how do we audit them?

## The seven shipped agents

| Agent | Focus area | One-line job |
|---|---|---|
| [`novelist`](novelist/AGENT.md) | Long-form fiction (NovelForge) | Run the four-phase NovelForge workflow — treat a novel as a stateful, temporally-consistent, knowledge-masked KB rather than a blob of text. |

See [CHECKLIST.md](CHECKLIST.md) for current build status of each agent and
its dependent skills.

## How agents relate to existing meta-skills

| Concept | Lives in | Loaded when | Scope |
|---|---|---|---|
| **Instruction** | `INSTRUCTIONS/` | Always | Universal principles, conventions, language standards. |
| **Skill** | `skills/<group>/<name>/` | Description matches user prompt | One task, one job, one handoff. |
| **Agent** | `agents/<name>/` | A scenario fires, or the user invokes the agent by role | A full *job* spanning multiple skills + phases. |
| **Scenario** | `SCENARIOS.md` | Playbook lookup | Documents *how an agent or chain runs* for a recognised situation. |

## Agent invocation

Three ways an agent fires:

1. **By name.** *"Use the lifecycle-pilot agent to take this idea through
   to launch."*
2. **By scenario match.** A request matches the agent's "When to fire"
   triggers; the orchestrator picks the agent instead of an ad-hoc chain.
3. **By another agent.** `scenario-strategist` may form a *group* of
   agents to execute a complex scenario (e.g. *"upgrade this monolith to
   microservices and re-launch"* → architecture-shepherd + devops-engineer
   + lifecycle-pilot working in concert).

## Agent file structure

Each agent folder contains:

```
agents/<agent-name>/
├── AGENT.md              # frontmatter + role + workflow + skills + deliverables
├── checklist.md          # (optional) per-agent execution checklist template
└── references/           # (optional) reference docs the agent loads on demand
```

The `AGENT.md` frontmatter follows this shape:

```yaml
---
name: <kebab-case-name>
role: <one-line persona>
focus_area: <one of: narrative>
status: shipped | stub | draft
fires_on:
  - <trigger phrase or scenario>
skills_used:
  shipped: [list]
  proposed: [list of skills to build]
deliverables:
  - <one per major output>
companion_agents: [list]
---
```

## Adding a new agent

1. Identify a recurring chain of skills that handles a coherent *job*
   (not a single task — that's a skill).
2. Run `scenario-strategist` to formalise the workflow and skill list.
3. Create `agents/<name>/AGENT.md` with the frontmatter above.
4. Register the agent in [CHECKLIST.md](CHECKLIST.md) and in this
   README's table.
5. Add a scenario to `SCENARIOS.md` documenting when this agent fires.
6. Wire into `skill-orchestrator`'s catalogue read so the orchestrator
   prefers the named agent over re-planning the chain.

## Anti-patterns

- **Agent = wrapper around one skill.** If the agent's whole workflow is
  *call skill X*, that's just the skill. Don't add an agent layer.
- **Agent without a deliverable contract.** *"Help with devops"* is not
  an agent — it's a category. An agent owns specific artifacts.
- **Agent that hard-codes skill names.** Skills evolve. The agent should
  reference skills by role (*"the production frontend skill"*) and let
  the orchestrator resolve to the current name.
- **Two agents owning the same artifact.** Each deliverable has exactly
  one agent on the hook. Co-ownership means nobody is on the hook.

## Companion docs

- [CHECKLIST.md](CHECKLIST.md) — build status across all agents and their
  dependent skills. **This is where you track progress.**
