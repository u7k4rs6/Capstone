"""seed demo inventory"""

import sqlalchemy as sa
from alembic import op

revision = "0002_seed_items"
down_revision = "0001_create_items"
branch_labels = None
depends_on = None

items = sa.table(
    "items",
    sa.column("name", sa.String),
    sa.column("sku", sa.String),
    sa.column("category", sa.String),
    sa.column("quantity", sa.Integer),
    sa.column("reorder_level", sa.Integer),
    sa.column("unit_price", sa.Float),
    sa.column("supplier", sa.String),
)

SEED = [
    ("Arabica Coffee Beans 1kg", "COF-ARB-1K", "Pantry", 42, 10, 18.5, "Blue Hill Roasters"),
    ("Oat Milk 1L", "MLK-OAT-1L", "Dairy", 6, 12, 2.4, "GreenFields"),
    ("Paper Cups 12oz (50)", "CUP-12-50", "Packaging", 0, 5, 7.9, "PackRight"),
    ("Espresso Machine Descaler", "CLN-DESC-01", "Cleaning", 9, 3, 12.0, "BrewCare"),
    ("Croissant Dough Tray", "BAK-CRS-TR", "Bakery", 15, 8, 22.0, "Maison Flour"),
    ("Vanilla Syrup 750ml", "SYR-VAN-750", "Pantry", 3, 4, 9.75, "Sweet Drop Co"),
]


def upgrade():
    op.bulk_insert(
        items,
        [dict(zip(["name", "sku", "category", "quantity", "reorder_level", "unit_price", "supplier"], row)) for row in SEED],
    )


def downgrade():
    op.execute(items.delete().where(items.c.sku.in_([row[1] for row in SEED])))
