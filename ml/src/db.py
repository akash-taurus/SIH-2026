"""Optional PostgreSQL persistence. Set DATABASE_URL to enable it."""
import os
from datetime import datetime
from sqlalchemy import create_engine, text

DATABASE_URL=os.getenv("DATABASE_URL")
_engine=create_engine(DATABASE_URL,pool_pre_ping=True) if DATABASE_URL else None

def init_db():
    if not _engine: return False
    with _engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS risk_predictions (
          id BIGSERIAL PRIMARY KEY, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,
          risk_score DOUBLE PRECISION NOT NULL, risk_level VARCHAR(20) NOT NULL,
          model_version VARCHAR(50), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS risk_alerts (
          id BIGSERIAL PRIMARY KEY, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,
          risk_score DOUBLE PRECISION NOT NULL, risk_level VARCHAR(20) NOT NULL,
          severity VARCHAR(20) NOT NULL, message TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"""))
    return True

def save_prediction(item):
    if not _engine: return
    with _engine.begin() as c:
        c.execute(text("INSERT INTO risk_predictions(lat,lon,risk_score,risk_level,model_version) VALUES (:lat,:lon,:score,:level,:version)"), item)

def save_alert(item):
    if not _engine: return
    with _engine.begin() as c:
        c.execute(text("INSERT INTO risk_alerts(lat,lon,risk_score,risk_level,severity,message) VALUES (:lat,:lon,:score,:level,:severity,:message)"), item)
