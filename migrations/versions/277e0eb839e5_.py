"""empty message

Revision ID: 277e0eb839e5
Revises: 17d11603bd73
Create Date: 2020-11-19 15:51:43.971040

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2.types import Geometry


# revision identifiers, used by Alembic.
revision = '277e0eb839e5'
down_revision = '17d11603bd73'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('locale', sa.String(), nullable=True))
    op.add_column('users', sa.Column('location', Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'location')
    op.drop_column('users', 'locale')
    # ### end Alembic commands ###
