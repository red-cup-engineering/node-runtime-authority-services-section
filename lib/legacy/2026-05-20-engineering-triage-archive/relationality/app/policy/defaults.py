"""Default policy definitions for the relational computer.

These policies implement the discipline/filter rules from the policy-stack
theorem and specifications. They provide a baseline governance model that
allows normal operations while protecting invariants.
"""

from __future__ import annotations

from app.schemas.policy import (
    PolicyDefinition,
    PolicyEffect,
    PolicyScope,
    DisciplineRule,
    FilterRule,
)


def create_default_policies() -> list[PolicyDefinition]:
    """Create the default policy definitions.
    
    Returns:
        List of PolicyDefinition objects for the base policies.
    """
    return [
        PolicyDefinition(
            id="intake-policy",
            name="Intake Stack Policy",
            description="Governs which observations may enter the system. Aligns with intake-stack simulation spec.",
            version="1.0.0",
            scope=PolicyScope.RECOGNITION,
            disciplines=[
                DisciplineRule(
                    id="require-acts",
                    name="Require Act References",
                    description="All recognitions must reference at least one valid act",
                    match_types=[],
                    match_acts=[],
                    match_tags=[],
                    effect=PolicyEffect.ALLOW,
                    priority=100,
                ),
                DisciplineRule(
                    id="deny-empty-content",
                    name="Deny Empty Content",
                    description="Reject recognitions with completely empty content",
                    match_types=[],
                    match_acts=[],
                    match_tags=["empty-content"],
                    effect=PolicyEffect.DENY,
                    priority=200,
                ),
            ],
            filters=[
                FilterRule(
                    id="mask-sensitive",
                    name="Mask Sensitive Fields",
                    description="Mask fields marked as sensitive in metadata",
                    match_path="metadata.sensitive",
                    action="mask",
                    applies_to_scope=PolicyScope.RECOGNITION,
                ),
            ],
            default_effect=PolicyEffect.ALLOW,
            tags=["intake", "observation", "default"],
        ),
        
        PolicyDefinition(
            id="runbook-policy",
            name="Runbook Execution Policy",
            description="Governs runbook creation and execution. Aligns with policy-stack theorem.",
            version="1.0.0",
            scope=PolicyScope.RUNBOOK,
            disciplines=[
                DisciplineRule(
                    id="require-steps",
                    name="Require Valid Steps",
                    description="Runbooks must have at least one step",
                    match_types=[],
                    match_acts=[],
                    match_tags=[],
                    effect=PolicyEffect.ALLOW,
                    priority=100,
                ),
                DisciplineRule(
                    id="deny-dangerous-acts",
                    name="Deny Dangerous Acts",
                    description="Block execution of dangerous acts without approval",
                    match_types=[],
                    match_acts=["delete-all", "drop-baseline", "reset-trace"],
                    match_tags=["dangerous"],
                    effect=PolicyEffect.REQUIRE_APPROVAL,
                    priority=300,
                ),
            ],
            filters=[],
            default_effect=PolicyEffect.ALLOW,
            tags=["runbook", "execution", "default"],
        ),
        
        PolicyDefinition(
            id="snapshot-policy",
            name="Snapshot Policy",
            description="Governs snapshot creation and access. Aligns with storage simulation spec.",
            version="1.0.0",
            scope=PolicyScope.SNAPSHOT,
            disciplines=[
                DisciplineRule(
                    id="allow-snapshots",
                    name="Allow Snapshot Creation",
                    description="Allow creating snapshots for persistence",
                    match_types=[],
                    match_acts=[],
                    match_tags=[],
                    effect=PolicyEffect.ALLOW,
                    priority=100,
                ),
            ],
            filters=[],
            default_effect=PolicyEffect.ALLOW,
            tags=["snapshot", "storage", "default"],
        ),
        
        PolicyDefinition(
            id="audit-policy",
            name="Audit Trail Policy",
            description="Ensures all operations are properly audited. Aligns with audit-stack theorem.",
            version="1.0.0",
            scope=PolicyScope.GLOBAL,
            disciplines=[
                DisciplineRule(
                    id="trace-all-writes",
                    name="Trace All Writes",
                    description="All write operations must have trace IDs",
                    match_types=[],
                    match_acts=[],
                    match_tags=[],
                    effect=PolicyEffect.ALLOW,
                    priority=50,
                ),
            ],
            filters=[],
            default_effect=PolicyEffect.ALLOW,
            tags=["audit", "traceability", "default"],
        ),
    ]


def load_default_policies(engine) -> None:
    """Load default policies into the policy engine.
    
    Args:
        engine: PolicyEngine instance to load policies into.
    """
    for policy in create_default_policies():
        engine.register_policy(policy)
