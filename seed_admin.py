from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

def create_initial_admin():
    db = SessionLocal()
    
    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == "admin@safestay.com").first()
    if existing_admin:
        print("Admin already exists!")
        return

    # Create the Admin User
    admin_user = User(
        full_name="Super Admin",
        email="admin@safestay.com",
        password_hash=hash_password("admin123"), # This will be securely hashed
        role="ADMIN",
        is_verified=True # Admin is pre-verified
    )

    try:
        db.add(admin_user)
        db.commit()
        print("Admin created successfully!")
        print("Email: admin@safestay.com")
        print("Password: admin123")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin()