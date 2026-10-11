"""Policy engine for evaluating policies against targets.

Implements the discipline/filter algebra from the policy specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.schemas.policy import (
    PolicyDefinition,
    PolicyEffect,
    PolicyScope,
    DisciplineRule,
    FilterRule,
    PolicyDecision,
)


@dataclass
class PolicyDecisionResult:
    """Result of a policy evaluation."""
    
    allowed: bool
    effect: PolicyEffect
    matched_rules: list[str] = field(default_factory=list)
    applied_filters: list[str] = field(default_factory=list)
    reasoning: str = ""
    requires_approval: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "effect": self.effect.value,
            "matched_rules": self.matched_rules,
            "applied_filters": self.applied_filters,
            "reasoning": self.reasoning,
            "requires_approval": self.requires_approval,
        }


class PolicyEngine:
    """Engine for evaluating policies."""
    
    def __init__(self, policies: Optional[list[PolicyDefinition]] = None):
        self._policies: dict[str, PolicyDefinition] = {}
        
        if policies:
            for policy in policies:
                self.register_policy(policy)
    
    def register_policy(self, policy: PolicyDefinition) -> None:
        """Register a policy definition."""
        self._policies[policy.id] = policy
    
    def get_policy(self, policy_id: str) -> Optional[PolicyDefinition]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> list[PolicyDefinition]:
        """List all registered policies."""
        return list(self._policies.values())
    
    def evaluate(
        self,
        target: dict[str, Any],
        scope: PolicyScope = PolicyScope.RECOGNITION,
        policy_ids: Optional[list[str]] = None,
    ) -> PolicyDecisionResult:
        """Evaluate policies against a target.
        
        Args:
            target: The data to evaluate (recognition, runbook step, etc.).
            scope: The scope of evaluation.
            policy_ids: Optional list of specific policies to evaluate.
        
        Returns:
            PolicyDecisionResult indicating whether the action is allowed.
        """
        policies = self._get_applicable_policies(scope, policy_ids)
        
        if not policies:
            return PolicyDecisionResult(
                allowed=True,
                effect=PolicyEffect.ALLOW,
                reasoning="No applicable policies found",
            )
        
        result = PolicyDecisionResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            reasoning="",
        )
        
        for policy in policies:
            policy_result = self._evaluate_policy(policy, target)
            
            if policy_result.effect == PolicyEffect.DENY:
                return PolicyDecisionResult(
                    allowed=False,
                    effect=PolicyEffect.DENY,
                    matched_rules=policy_result.matched_rules,
                    reasoning=f"Denied by policy '{policy.id}': {policy_result.reasoning}",
                )
            
            if policy_result.effect == PolicyEffect.REQUIRE_APPROVAL:
                result.requires_approval = True
                result.effect = PolicyEffect.REQUIRE_APPROVAL
            
            result.matched_rules.extend(policy_result.matched_rules)
            result.applied_filters.extend(policy_result.applied_filters)
        
        if result.requires_approval:
            result.allowed = False
            result.reasoning = "Requires approval"
        else:
            result.reasoning = "Allowed by all policies"
        
        return result
    
    def apply_filters(
        self,
        target: dict[str, Any],
        scope: PolicyScope = PolicyScope.RECOGNITION,
        policy_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Apply filter rules to transform/mask content.
        
        Args:
            target: The data to filter.
            scope: The scope of filtering.
            policy_ids: Optional list of specific policies to apply.
        
        Returns:
            Filtered/transformed data.
        """
        policies = self._get_applicable_policies(scope, policy_ids)
        result = dict(target)
        
        for policy in policies:
            for filter_rule in policy.filters:
                if filter_rule.applies_to_scope != scope:
                    continue
                
                result = self._apply_filter(filter_rule, result)
        
        return result
    
    def _get_applicable_policies(
        self,
        scope: PolicyScope,
        policy_ids: Optional[list[str]] = None,
    ) -> list[PolicyDefinition]:
        """Get policies applicable to a scope."""
        if policy_ids:
            return [
                self._policies[pid]
                for pid in policy_ids
                if pid in self._policies
            ]
        
        return [
            policy for policy in self._policies.values()
            if policy.scope == scope or policy.scope == PolicyScope.GLOBAL
        ]
    
    def _evaluate_policy(
        self,
        policy: PolicyDefinition,
        target: dict[str, Any],
    ) -> PolicyDecisionResult:
        """Evaluate a single policy against a target."""
        matched_rules: list[str] = []
        
        disciplines = sorted(
            policy.disciplines,
            key=lambda d: d.priority,
            reverse=True,
        )
        
        for rule in disciplines:
            if self._rule_matches(rule, target):
                matched_rules.append(rule.id)
                
                if rule.effect == PolicyEffect.DENY:
                    return PolicyDecisionResult(
                        allowed=False,
                        effect=PolicyEffect.DENY,
                        matched_rules=matched_rules,
                        reasoning=f"Matched deny rule: {rule.name}",
                    )
                
                if rule.effect == PolicyEffect.REQUIRE_APPROVAL:
                    return PolicyDecisionResult(
                        allowed=False,
                        effect=PolicyEffect.REQUIRE_APPROVAL,
                        matched_rules=matched_rules,
                        reasoning=f"Matched approval rule: {rule.name}",
                        requires_approval=True,
                    )
        
        if not matched_rules:
            return PolicyDecisionResult(
                allowed=policy.default_effect == PolicyEffect.ALLOW,
                effect=policy.default_effect,
                reasoning=f"No rules matched, using default: {policy.default_effect.value}",
            )
        
        return PolicyDecisionResult(
            allowed=True,
            effect=PolicyEffect.ALLOW,
            matched_rules=matched_rules,
            reasoning="All matched rules allow",
        )
    
    def _rule_matches(
        self,
        rule: DisciplineRule,
        target: dict[str, Any],
    ) -> bool:
        """Check if a discipline rule matches the target."""
        target_tags = set(target.get("tags", []))
        if rule.match_tags and not target_tags.intersection(rule.match_tags):
            return False
        
        target_acts = set(target.get("acts", []))
        if rule.match_acts and not target_acts.intersection(rule.match_acts):
            return False
        
        target_type = target.get("type")
        if rule.match_types and target_type not in rule.match_types:
            return False
        
        if not rule.match_tags and not rule.match_acts and not rule.match_types:
            return True
        
        return True
    
    def _apply_filter(
        self,
        filter_rule: FilterRule,
        target: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply a single filter rule to the target."""
        result = dict(target)
        
        if filter_rule.action == "mask":
            path = filter_rule.match_path
            if path != "*" and path in result:
                result[path] = "***MASKED***"
        
        elif filter_rule.action == "remove":
            path = filter_rule.match_path
            if path != "*" and path in result:
                del result[path]
        
        elif filter_rule.action == "transform":
            pass
        
        return result


_default_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get the default policy engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = PolicyEngine()
    return _default_engine
