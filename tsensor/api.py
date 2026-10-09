import math
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tsensor.analytics import FIELDS, monitoring_report
from tsensor.codec import decode_response
from tsensor.db import Base, Device, Organization, Reading, make_database
from tsensor.schemas import DeviceInput, FrameInput, OrganizationInput, ReadingInput


def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def save_reading(factory, org_id, device_id, payload):
    with factory.begin() as session:
        if session.get(Device, (org_id, device_id)) is None:
            raise HTTPException(404, "Device is not registered in this organization")
        previous = session.scalar(
            select(Reading).where(
                Reading.org_id == org_id,
                Reading.device_id == device_id,
                Reading.observed_at == payload.observed_at,
            )
        )
        if previous:
            matches = all(
                math.isclose(getattr(previous, key), getattr(payload, key), rel_tol=0, abs_tol=1e-9)
                for key in FIELDS
            )
            if (
                not matches
                or previous.source != payload.source
                or (previous.raw_frame_hex != payload.raw_frame_hex)
            ):
                raise HTTPException(409, "This timestamp already has different telemetry")
            return {"reading_id": previous.id, "duplicate": True}
        row = Reading(org_id=org_id, device_id=device_id, **payload.model_dump())
        session.add(row)
        session.flush()
        return {"reading_id": row.id, "duplicate": False}


def create_app(database_url=None, api_token=None):
    engine, factory = make_database(database_url)
    token = api_token if api_token is not None else os.getenv("API_TOKEN")

    def authorize(x_api_key: str | None = Header(default=None)):
        if token and not secrets.compare_digest(x_api_key or "", token):
            raise HTTPException(401, "Invalid API key")

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="T-Sensor", version="0.1.0", lifespan=lifespan, dependencies=[Depends(authorize)]
    )
    app.state.session_factory = factory
    app.state.engine = engine

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, error: IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Duplicate or invalid reference"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/organizations", status_code=201)
    def organization(payload: OrganizationInput):
        with factory.begin() as session:
            session.add(Organization(**payload.model_dump()))
        return payload.model_dump()

    @app.post("/organizations/{org_id}/devices", status_code=201)
    def device(org_id: str, payload: DeviceInput):
        with factory.begin() as session:
            if session.get(Organization, org_id) is None:
                raise HTTPException(404, "Organization not found")
            session.add(Device(org_id=org_id, id=payload.id))
        return {"org_id": org_id, "device_id": payload.id}

    @app.post("/organizations/{org_id}/devices/{device_id}/readings")
    def reading(org_id: str, device_id: str, payload: ReadingInput):
        return save_reading(factory, org_id, device_id, payload)

    @app.post("/organizations/{org_id}/devices/{device_id}/frames")
    def frame(org_id: str, device_id: str, payload: FrameInput):
        try:
            values = decode_response(bytes.fromhex(payload.frame_hex), address=payload.address)
            parsed = ReadingInput(
                **values,
                observed_at=payload.observed_at,
                source=payload.source,
                raw_frame_hex=payload.frame_hex.lower(),
            )
        except (ValueError, ValidationError) as error:
            raise HTTPException(422, "Frame validation failed: " + str(error)) from error
        return save_reading(factory, org_id, device_id, parsed)

    @app.get("/organizations/{org_id}/devices/{device_id}/readings")
    def readings(org_id: str, device_id: str, limit: int = Query(100, ge=1, le=2000)):
        with factory() as session:
            return [
                row_dict(row)
                for row in session.scalars(
                    select(Reading)
                    .where(
                        Reading.org_id == org_id,
                        Reading.device_id == device_id,
                    )
                    .order_by(Reading.observed_at.desc())
                    .limit(limit)
                )
            ]

    @app.get("/organizations/{org_id}/devices/{device_id}/monitoring")
    def monitoring(org_id: str, device_id: str, hours: int = Query(24, ge=1, le=168)):
        with factory() as session:
            return monitoring_report(session, org_id, device_id, hours=hours)

    return app


app = create_app()
