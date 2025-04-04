"""initial migration

Revision ID: bad8138b8a19
Revises: 
Create Date: 2025-01-20 18:28:57.589958

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bad8138b8a19'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sent_email',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('job_url', sa.String(), nullable=False),
    sa.Column('position', sa.String(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('email', 'job_url', 'position', 'location')
    )
    op.create_table('users',
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('position', sa.String(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('job_type', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('email', 'position', 'location')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')
    op.drop_table('sent_email')
    # ### end Alembic commands ###
