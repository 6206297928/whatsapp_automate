import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

_DB_URL = os.environ.get("DATABASE_URL", "postgresql://myuser:mypassword@localhost:5432/mydb")

Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, default="Test User")
    linked = Column(Boolean, nullable=False, default=True)
    linked_to = Column(String, nullable=False, default='customer') # customer, vendor
    entity_id = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    customer_id = Column(String, nullable=False)
    linked_user_id = Column(String, nullable=False)
    customer_message = Column(String, nullable=True)
    type = Column(String, default='rfq')
    status = Column(String, default='Open')
    created_at = Column(DateTime, default=datetime.utcnow)
    vendors = relationship("TicketVendor", back_populates="ticket")

class TicketVendor(Base):
    __tablename__ = 'ticket_vendors'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String, ForeignKey('tickets.id'), nullable=False)
    vendor_entity_id = Column(String, nullable=False)
    vendor_response = Column(String, nullable=True)
    delivery_info = Column(String, default='not_mentioned')
    status = Column(String, default='Pending')
    ticket = relationship("Ticket", back_populates="vendors")

engine = create_engine(_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    return SessionLocal()

def generate_ticket_number(session):
    count = session.query(Ticket).count()
    return f"IT-{datetime.utcnow().strftime('%y%m%d')}-Loc-{count + 1:04d}"
