"""Single shared mechanism for tenant scoping (ADR 0001).

Every tenant-owned query must go through ScopedQuery. It never returns,
updates, or creates rows outside the bound tenant, so handlers cannot
forget to scope.
"""

from typing import TypeVar

from sqlalchemy.orm import Session

from .models import Base

T = TypeVar("T", bound=Base)


class ScopedQuery:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def _check(self, instance: T) -> T:
        if getattr(instance, "tenant_id", None) != self.tenant_id:
            raise ValueError(f"{type(instance).__name__} has no tenant_id; it cannot be scoped")
        return instance

    def all(self, model: type[T], **filters) -> list[T]:
        return self.db.query(model).filter(model.tenant_id == self.tenant_id).filter_by(**filters).all()

    def get(self, model: type[T], id: str) -> T | None:
        instance = self.db.get(model, id)
        if instance is None or getattr(instance, "tenant_id", None) != self.tenant_id:
            return None
        return instance

    def get_by(self, model: type[T], **filters) -> T | None:
        instance = self.db.query(model).filter_by(**filters).first()
        if instance is None or getattr(instance, "tenant_id", None) != self.tenant_id:
            return None
        return instance

    def add(self, instance: T) -> T:
        self.db.add(self._check(instance))
        return instance
