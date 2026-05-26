from enum import Enum
from dataclasses import dataclass


class MechanismCategory(Enum):
    DYNAMICS = 'dynamics'
    COSMETIC = 'cosmetic'


ALLOWED_DYNAMICS = ['fear', 'migration', 'scarcity', 'territory', 'fertility', 'climate']
REJECTED_COSMETICS = ['furniture', 'shoes', 'literary_chat', 'decorative_items', 'clothing', 'accessories']


@dataclass
class GovernorVerdict:
    approved: bool
    category: MechanismCategory
    reason: str

    def to_dict(self) -> dict:
        return {
            'approved': self.approved,
            'category': self.category.value,
            'reason': self.reason,
        }


class ComplexityGovernor:
    def evaluate(self, proposal: dict) -> GovernorVerdict:
        dynamics = proposal.get('affects_dynamics', [])

        # 1. Intersection with ALLOWED_DYNAMICS → approved, DYNAMICS
        if any(d in ALLOWED_DYNAMICS for d in dynamics):
            return GovernorVerdict(
                approved=True,
                category=MechanismCategory.DYNAMICS,
                reason=f"Mechanism affects allowed dynamics: {[d for d in dynamics if d in ALLOWED_DYNAMICS]}",
            )

        # 2. Empty or all REJECTED_COSMETICS → rejected, COSMETIC
        if not dynamics or all(d in REJECTED_COSMETICS for d in dynamics):
            return GovernorVerdict(
                approved=False,
                category=MechanismCategory.COSMETIC,
                reason="Proposal is purely cosmetic and does not affect world dynamics.",
            )

        # 3. Unknown terms → rejected
        unknown = [d for d in dynamics if d not in ALLOWED_DYNAMICS and d not in REJECTED_COSMETICS]
        return GovernorVerdict(
            approved=False,
            category=MechanismCategory.COSMETIC,
            reason=f"Unknown dynamics terms: {unknown}",
        )
