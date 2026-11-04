"""SQLAlchemy 2 Declarative Base configuration.

Application entities must not be defined during foundation setup.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all future SQLAlchemy models."""

    pass
