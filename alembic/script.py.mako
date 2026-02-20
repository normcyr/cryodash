"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
% if globals().get('upgrade_ops'):
    ${globals().get('upgrade_ops')}
% else:
    pass
% endif


def downgrade():
% if globals().get('downgrade_ops'):
    ${globals().get('downgrade_ops')}
% else:
    pass
% endif
