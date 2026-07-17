import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA
from sqlalchemy.orm import relationship
from .base import Base

# --- DOCTORS TABLE ---
class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    specialty = Column(Text)
    calendar_id = Column(Text)
    working_hours = Column(JSONB)
    created_at = Column(DateTime)

    appointments = relationship("Appointment", back_populates="doctor")

# --- PATIENTS TABLE ---
class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True)
    created_at = Column(DateTime)

    appointments = relationship("Appointment", back_populates="patient")
    interaction_logs = relationship("InteractionLog", back_populates="patient")

# --- APPOINTMENTS TABLE ---
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"))
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    calendar_event_id = Column(Text)
    created_at = Column(DateTime)
    status = Column(Text)

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    execution_logs = relationship("ExecutionLog", back_populates="appointment")

# --- VERIFICATION CODES ---
class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text)
    code = Column(Text)
    request_id = Column(Text)
    created_at = Column(DateTime)
    is_verified = Column(Boolean, default=False)
    name = Column(Text)

# --- LOGGING TABLES ---
class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    action = Column(Text)
    status = Column(Text)
    message = Column(Text)
    created_at = Column(DateTime)

    appointment = relationship("Appointment", back_populates="execution_logs")

class InteractionLog(Base):
    __tablename__ = "interaction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"))
    summary = Column(Text)
    timestamp = Column(DateTime)

    patient = relationship("Patient", back_populates="interaction_logs")