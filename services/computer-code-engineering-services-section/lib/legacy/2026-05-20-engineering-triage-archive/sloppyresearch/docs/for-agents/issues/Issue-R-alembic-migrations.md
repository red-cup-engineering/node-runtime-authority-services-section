+++
id = "issue.R"
title = "Set up Alembic migrations for the RRPR database"
status = "open"
priority = "p2"
area = "database"
document_type = "issue"
topics = ["database", "migrations"]
created = "2025-11-10"
owner = ""
+++

Context
- Schema changes are currently manual; `guidelines.agents.md` lists “Setting up Alembic migrations” as an outstanding task.
- Without migrations we cannot evolve RelCells/Edges/Provenance safely or share upgrades between agents.

Acceptance
- [ ] Initialize Alembic in the repo (env script, migrations folder) targeting the SQLite graph schema defined in `src/code/rrpi/database.py`.
- [ ] Capture current schema as the base migration and document how to generate/apply migrations.
- [ ] Integrate migration commands into runbooks/CLI (`python -m rrpi.cli.main db upgrade` or similar).

Links
- src/code/rrpi/database.py
- guidelines.agents.md (Current Refactoring Status)
