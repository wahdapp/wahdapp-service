"""empty message

Revision ID: c0e8a94dc4cf
Revises: e7e582568c72
Create Date: 2020-06-28 19:15:09.189370

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0e8a94dc4cf'
down_revision = 'e7e582568c72'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prayers', sa.Column('inviter_id', sa.String(), nullable=True))
    op.drop_constraint('prayers_inviter_fkey', 'prayers', type_='foreignkey')
    op.create_foreign_key(None, 'prayers', 'users', ['inviter_id'], ['id'])
    op.drop_column('prayers', 'inviter')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prayers', sa.Column('inviter', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'prayers', type_='foreignkey')
    op.create_foreign_key('prayers_inviter_fkey', 'prayers', 'users', ['inviter'], ['id'])
    op.drop_column('prayers', 'inviter_id')
    # ### end Alembic commands ###
