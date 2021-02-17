"""empty message

Revision ID: 1c236ffcb822
Revises: 277e0eb839e5
Create Date: 2020-11-26 14:47:23.040419

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c236ffcb822'
down_revision = '277e0eb839e5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('prayers', 'same_gender')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prayers', sa.Column('same_gender', sa.BOOLEAN(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
