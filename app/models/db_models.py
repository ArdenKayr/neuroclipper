from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    subscription_type = Column(String, default='нарезчик')
    is_superuser = Column(Boolean, default=False)
    balance_clips = Column(Integer, default=0)
    user_settings = Column(JSON, default={})
    
    presets = relationship("Preset", back_populates="owner")
    channels = relationship("Channel", back_populates="owner")

class Preset(Base):
    __tablename__ = 'presets'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey('users.id'))
    platform = Column(String)
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
    created_at = Column(DateTime, default=datetime.utcnow)