from app.database import Base, engine
from app.models import User

print("Connecting to MSSQL and creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")