from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum as SqlAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func # For server-side default timestamps if needed, though Pydantic handles client-side
import datetime # For default values

from .database import Base
# Import Pydantic enums to be reused by SQLAlchemy's Enum type
from .data_models import LeadProcessingStatusEnum, AgentExecutionStatusEnum

class LeadProcessingStateOrm(Base):
    __tablename__ = "leads_processing_state"

    lead_id = Column(String, primary_key=True, index=True)
    run_id = Column(String, index=True, nullable=False)
    url = Column(String, nullable=True)
    status = Column(SqlAlchemyEnum(LeadProcessingStatusEnum, name="lead_processing_status_enum"), nullable=False, default=LeadProcessingStatusEnum.PENDING)
    current_agent = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_update_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    final_package_summary = Column(Text, nullable=True) # Store as JSON string

    # Relationship: One LeadProcessingState can have many AgentExecutionRecords
    agent_records = relationship("AgentExecutionRecordOrm", back_populates="lead_state", cascade="all, delete-orphan")

class AgentExecutionRecordOrm(Base):
    __tablename__ = "agent_execution_records"

    record_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(String, ForeignKey("leads_processing_state.lead_id"), nullable=False, index=True)
    agent_name = Column(String, nullable=False)
    status = Column(SqlAlchemyEnum(AgentExecutionStatusEnum, name="agent_execution_status_enum"), nullable=False)
    start_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True) # Store agent's Pydantic output model as JSON string
    metrics_json = Column(Text, nullable=True) # Store BaseAgent metrics as JSON string
    error_message = Column(Text, nullable=True)

    # Relationship: Many AgentExecutionRecords belong to one LeadProcessingState
    lead_state = relationship("LeadProcessingStateOrm", back_populates="agent_records")