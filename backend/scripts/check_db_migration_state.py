import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from app.core.config import get_settings
engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    print("alembic", conn.execute(text("SELECT version_num FROM alembic_version")).scalar())
    print("phone_col", conn.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='crm_customers' AND column_name='phone'")).scalar())
    print("version_col_len", conn.execute(text("SELECT character_maximum_length FROM information_schema.columns WHERE table_name='alembic_version' AND column_name='version_num'")).scalar())
