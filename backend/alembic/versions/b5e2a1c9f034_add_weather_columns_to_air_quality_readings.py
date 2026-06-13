"""add_weather_columns_to_air_quality_readings

Revision ID: b5e2a1c9f034
Revises: c7a1f3d92e08
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5e2a1c9f034"
down_revision: Union[str, None] = "c7a1f3d92e08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("air_quality_readings", sa.Column("temperature", sa.Numeric(5, 2), nullable=True))
    op.add_column("air_quality_readings", sa.Column("humidity", sa.Numeric(5, 2), nullable=True))
    op.add_column("air_quality_readings", sa.Column("wind_speed", sa.Numeric(6, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("air_quality_readings", "wind_speed")
    op.drop_column("air_quality_readings", "humidity")
    op.drop_column("air_quality_readings", "temperature")
