# Runbooks

This directory contains YAML runbook definitions for the universal relational computer.

## Overview

A **runbook** is a sequence of steps that map to mathematical **acts** in the relational calculus. Every step in a runbook must reference one or more acts from `docs/math/acts/`, ensuring that all operations are formally justified and traceable.

## Directory Structure

```
runbooks/
├── README.md           # This file
└── examples/           # Example runbooks
    ├── intake-observation.yaml
    ├── witness-judgement.yaml
    └── validate-and-store.yaml
```

## Runbook Format

Runbooks are defined in YAML with the following structure:

```yaml
name: Runbook Name
description: What this runbook does
version: "1.0.0"
tags:
  - category
  - purpose
policy_requirements:
  - required-policy-id

steps:
  - id: step-identifier
    name: Human Readable Name
    description: What this step does
    acts:
      - act-slug-1
      - act-slug-2
    depends_on:
      - previous-step-id
    inputs:
      - name: input_name
        type: string
        required: true
        from_step: other_step.output_name
    outputs:
      - name: output_name
        type: object
    condition: optional_expression == true
    retry_count: 0
    timeout_seconds: 60
```

## Key Concepts

### Acts

Every step must reference at least one act. Acts are the atomic mathematical operations defined in `docs/math/acts/`. Examples:

- `seed-observation` - Seeds an initial observation
- `recognize-value` - Recognizes a value from an observation
- `witness-judgement` - Creates a witness for a judgement
- `normalize-observation` - Normalizes an observation for storage

### Dependencies

Steps can depend on other steps using `depends_on`. The execution engine will:
1. Build a dependency graph
2. Detect cycles (and reject invalid runbooks)
3. Execute steps in parallel when possible
4. Respect dependency ordering

### Input/Output Wiring

Outputs from one step can be wired to inputs of dependent steps:

```yaml
steps:
  - id: first
    outputs:
      - name: result

  - id: second
    depends_on:
      - first
    inputs:
      - name: data
        from_step: first.result
```

### Policy Requirements

Runbooks can declare required policies. Before execution, the policy engine will verify that all requirements are satisfied.

## API Usage

### Create a Runbook

```bash
curl -X POST http://localhost:5000/runbooks \
  -H "Content-Type: application/json" \
  -d '{"yaml": "name: Test\nsteps:\n  - id: s1\n    name: Step 1\n    acts: [seed-observation]"}'
```

### Validate a Runbook

```bash
curl -X POST http://localhost:5000/runbooks/validate \
  -H "Content-Type: application/json" \
  -d '{"yaml": "<runbook yaml content>"}'
```

### Execute a Runbook

```bash
curl -X POST http://localhost:5000/runbooks/{runbook_id}/execute \
  -H "Content-Type: application/json" \
  -d '{"payload": {"key": "value"}}'
```

## MCP Integration

Runbooks are also accessible via the MCP server:

- `list_runbooks()` - List all stored runbooks
- `validate_runbook(yaml_content)` - Validate a runbook YAML
- `execute_runbook(runbook_id, inputs)` - Execute a stored runbook

## Example Runbooks

### 1. Intake Observation (`examples/intake-observation.yaml`)

Demonstrates the canonical intake flow:
1. Seed the observation
2. Recognize the value
3. Normalize for storage

### 2. Witness Judgement (`examples/witness-judgement.yaml`)

Demonstrates the witnessing flow:
1. Start a trace
2. Create the witness
3. Record the step
4. Complete the trace

### 3. Validate and Store (`examples/validate-and-store.yaml`)

Full intake-to-storage flow with syntax validation and conditional execution.

## Extending Runbooks

To add support for new acts:

1. Ensure the act exists in `docs/math/acts/`
2. Create a handler in `app/rewriter/builtin_handlers.py`
3. Register the handler with the `HandlerRegistry`

Example handler:

```python
class MyActHandler(ActHandler):
    acts = ["my-new-act"]
    
    async def execute(self, act: str, context: ExecutionContext) -> HandlerResult:
        # Implementation
        return HandlerResult.ok(outputs={"result": value})
```
