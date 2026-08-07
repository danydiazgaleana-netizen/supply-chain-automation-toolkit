from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone
from .base import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    area_origen = Column(String(50), nullable=False)
    titulo = Column(String(100), nullable=False)
    mensaje = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=True)  # opcional: si quieres notificaciones por usuario
    leida = Column(Integer, default=0)        # 0 = no leída, 1 = leída