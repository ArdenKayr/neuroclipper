from sqlalchemy import Column, Integer, BigInteger, String, Boolean, JSON, DateTime, ForeignKey, Float
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    subscription_type = Column(String, default='нарезчик') # нарезчик, блогер, агентство
    is_superuser = Column(Boolean, default=False)
    balance_clips = Column(Integer, default=0)
    user_settings = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now())
    
    presets = relationship("Preset", back_populates="owner", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="owner", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user")
    transactions = relationship("TransactionLog", back_populates="user")

class TransactionLog(Base):
    __tablename__ = 'transaction_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Integer)  # Положительное (пополнение) или отрицательное (списание)
    type = Column(String)     # refill, spend, refund
    description = Column(String)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="transactions")

class Preset(Base):
    __tablename__ = 'presets'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey('users.id'))
    platform = Column(String) # TikTok, YouTube, Instagram
    config_data = Column(JSON, nullable=False)
    ad_media_path = Column(String, nullable=True)
    
    owner = relationship("User", back_populates="presets")

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'))
    url = Column(String, nullable=False)
    preset_id = Column(Integer, ForeignKey('presets.id'))
    is_active = Column(Boolean, default=True)
    
    owner = relationship("User", back_populates="channels")

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    input_url = Column(String)
    status = Column(String, default='pending') # pending, downloading, processing, done, error
    priority = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="jobs")