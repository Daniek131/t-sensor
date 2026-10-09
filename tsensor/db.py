import os
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class Device(Base):
    __tablename__ = "devices"
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (
        ForeignKeyConstraint(["org_id", "device_id"], ["devices.org_id", "devices.id"]),
        # I use one unique key for duplicate detection and device/time queries.
        UniqueConstraint("org_id", "device_id", "observed_at", name="uq_readings_device_time"),
        CheckConstraint("moisture >= 0 AND moisture <= 100 AND ph >= 0 AND ph <= 14"),
        CheckConstraint("temperature >= -50 AND temperature <= 100"),
        CheckConstraint("ec >= 0 AND ec <= 65535"),
        CheckConstraint("nitrogen >= 0 AND phosphorus >= 0 AND potassium >= 0"),
        CheckConstraint("source IN ('hardware', 'synthetic', 'replay')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64))
    device_id: Mapped[str] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(20))
    raw_frame_hex: Mapped[str | None] = mapped_column(String(38))
    moisture: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    ec: Mapped[int]
    ph: Mapped[float] = mapped_column(Float)
    nitrogen: Mapped[int]
    phosphorus: Mapped[int]
    potassium: Mapped[int]


def make_database(url=None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./tsensor.db")
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def connect(connection, _):
            connection.isolation_level = None
            connection.execute("PRAGMA foreign_keys=ON")

        @event.listens_for(engine, "begin")
        def begin(connection):
            connection.exec_driver_sql("BEGIN")

    return engine, sessionmaker(engine, expire_on_commit=False)


if __name__ == "__main__":
    engine, _ = make_database()
    Base.metadata.create_all(engine)
    engine.dispose()
    print("Telemetry schema initialized.")
