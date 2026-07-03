"""Duplicate group review helpers and documented merge policy for a future merge workflow.

MERGE MUST NEVER LOSE FAIR PARTICIPATIONS.

Future merge behavior:
- Admin selects winner customer.
- All fair participations from loser customers move to winner.
- If winner already has the same fair, do not create duplicate fair participation.
- No fair participation may be lost.
- Loser customers are marked deleted only after all related records are reassigned to the winner.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

DUPLICATE_MERGE_POLICY = """
MERGE MUST NEVER LOSE FAIR PARTICIPATIONS.

Future merge behavior:
1. Admin selects a winner customer for the group.
2. All fair participations from loser customers are moved to the winner.
3. If the winner already participates in the same fair, keep the existing participation and skip creating a duplicate row.
4. No fair participation may be deleted or lost during merge.
5. Loser customer records are marked deleted only after every related record has been reassigned to the winner.
""".strip()


@dataclass(frozen=True)
class GroupMemberSnapshot:
    customer_id: UUID
    company_name: str
    created_at: datetime


def pick_suggested_winner_customer(
    members: list[GroupMemberSnapshot],
    participation_counts: dict[UUID, int],
) -> UUID:
    if not members:
        raise ValueError("Group has no members")

    def sort_key(member: GroupMemberSnapshot) -> tuple[int, float, str]:
        participation_count = participation_counts.get(member.customer_id, 0)
        created_ts = member.created_at.timestamp()
        return (-participation_count, created_ts, str(member.customer_id))

    return min(members, key=sort_key).customer_id
