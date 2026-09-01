import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..core.database import Base

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

class Supervisor(Base):
    __tablename__ = "supervisors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    base_instruction = Column(Text)
    config = Column(JSON) # e.g., default wake up behavior, model choice
    created_at = Column(DateTime, default=get_utc_now)

    runs = relationship("Run", back_populates="supervisor")


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, index=True) # UUID
    order_id = Column(String, index=True)
    supervisor_id = Column(Integer, ForeignKey("supervisors.id"))
    status = Column(String, default="active") # active, sleeping, completed
    state = Column(JSON, default={}) # serialized agent state
    next_wake_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    supervisor = relationship("Supervisor", back_populates="runs")
    activities = relationship("Activity", back_populates="run", cascade="all, delete-orphan")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, ForeignKey("runs.id"))
    type = Column(String) # event, action, instruction, sleep, wake, complete
    payload = Column(JSON) # event details, action details, etc.
    created_at = Column(DateTime, default=get_utc_now)

    run = relationship("Run", back_populates="activities")
