"""empty message

Revision ID: bab280519857
Revises: 
Create Date: 2020-06-07 14:58:32.236838

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'bab280519857'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('full_name', sa.Unicode(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('gender', sa.String(length=1), nullable=True),
    sa.Column('device_token', sa.String(), nullable=True),
    sa.Column('black_list', postgresql.HSTORE(text_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('filter_preferences',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('selected_prayers', sa.String(), nullable=True),
    sa.Column('distance', sa.Integer(), nullable=True),
    sa.Column('minimum_participants', sa.Integer(), nullable=True),
    sa.Column('same_gender', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('prayers',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('prayer', sa.String(), nullable=True),
    sa.Column('location', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('inviter', sa.String(), nullable=True),
    sa.Column('guests_male', sa.Integer(), nullable=True),
    sa.Column('guests_female', sa.Integer(), nullable=True),
    sa.Column('schedule_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['inviter'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('participations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('user_full_name', sa.Unicode(), nullable=True),
    sa.Column('user_gender', sa.String(length=1), nullable=True),
    sa.Column('prayer_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.ForeignKeyConstraint(['prayer_id'], ['prayers.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('participations')
    op.drop_table('prayers')
    op.drop_table('filter_preferences')
    op.drop_table('users')
    # ### end Alembic commands ###
