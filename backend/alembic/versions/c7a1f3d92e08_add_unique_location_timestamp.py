"""add_unique_location_timestamp

Revision ID: c7a1f3d92e08
Revises: eda89ba9c8e2
Create Date: 2026-06-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7a1f3d92e08'
down_revision: Union[str, None] = 'eda89ba9c8e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_location_timestamp",
        "air_quality_readings",
        ["location_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_location_timestamp", "air_quality_readings", type_="unique")
