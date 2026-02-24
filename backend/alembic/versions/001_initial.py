"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )

    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(10), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_countries"),
        sa.UniqueConstraint("name", name="uq_countries_name"),
    )

    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], name="fk_regions_country_id_countries"),
        sa.PrimaryKeyConstraint("id", name="pk_regions"),
    )

    op.create_table(
        "baths",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("description", sa.String(2048), nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("canonical_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], name="fk_baths_country_id_countries"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], name="fk_baths_region_id_regions"),
        sa.ForeignKeyConstraint(["canonical_id"], ["baths.id"], name="fk_baths_canonical_id_baths"),
        sa.PrimaryKeyConstraint("id", name="pk_baths"),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bath_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("flag_long", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flag_ultraunique", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["bath_id"], ["baths.id"], name="fk_visits_bath_id_baths"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_visits_created_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_visits"),
    )
    op.create_index("ix_visits_message_id", "visits", ["message_id", "chat_id"], unique=True)

    op.create_table(
        "visit_participants",
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], name="fk_visit_participants_visit_id_visits"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_visit_participants_user_id_users"),
        sa.PrimaryKeyConstraint("visit_id", "user_id", name="pk_visit_participants"),
    )

    op.create_table(
        "point_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_point_logs_user_id_users"),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], name="fk_point_logs_visit_id_visits"),
        sa.PrimaryKeyConstraint("id", name="pk_point_logs"),
    )

    op.create_table(
        "point_config",
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("description", sa.String(256), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("key", name="pk_point_config"),
    )


def downgrade() -> None:
    op.drop_table("point_config")
    op.drop_table("point_logs")
    op.drop_table("visit_participants")
    op.drop_index("ix_visits_message_id", table_name="visits")
    op.drop_table("visits")
    op.drop_table("baths")
    op.drop_table("regions")
    op.drop_table("countries")
    op.drop_table("users")
