from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

class UserDB(Base):
    __tablename__ = 'users'

    email = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=True)
    uid = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)
    points = Column(Integer, default=0)   # 0 points means user is not created in Stripe
    tier = Column(String(100), default="FREE")  # FREE, PERSONAL, BUSINESS, ENTERPRISE


class PostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://test_user:neko@65.109.162.178:5432/test_db"
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, email, name, uid, is_active, points, tier):
        try:
            session = self.Session()
            user = UserDB(email=email, name=name, uid=uid, is_active=is_active, points=points, tier=tier)
            session.add(user)
            session.commit()
            session.close()
            print("UserDB record inserted successfully")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def read(self, email=None):
        try:
            session = self.Session()
            if email:
                user = session.query(UserDB).filter_by(email=email).first()
                if user:
                    return [(user.email, user.name, user.uid, user.is_active, user.points, user.tier)]
            else:
                users = session.query(UserDB).all()
                return [(user.email, user.name, user.uid, user.is_active, user.points, user.tier) for user in users]
        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []

    def update(self, email, new_data):
        try:
            session = self.Session()
            user = session.query(UserDB).filter_by(email=email).first()
            if user:
                # Update user attributes as needed
                for key, value in new_data.items():
                    setattr(user, key, value)
                session.commit()
                session.close()
                print("UserDB record updated successfully")
            else:
                print("UserDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def delete(self, email):
        try:
            session = self.Session()
            user = session.query(UserDB).filter_by(email=email).first()
            if user:
                session.delete(user)
                session.commit()
                session.close()
                print("UserDB record deleted successfully")
            else:
                print("UserDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

# if __name__ == "__main__":
#     db = PostgreSQLCRUD()

#     # Create user records
#     db.create("john@example.com", "John Doe", "uid123", 1, 100, "FREE")
#     db.create("jane@example.com", "Jane Smith", "uid456", 1, 150, "PERSONAL")

#     # Read user records
#     records = db.read()
#     print("Read user records:", records)

#     # Update a user record
#     db.update("john@example.com", {"points": 400})

#     # Delete a user record
#     db.delete("jane@example.com")
