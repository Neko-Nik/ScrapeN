from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from src.utils.base.basic import retry


Base = declarative_base()


class UserDB(Base):
    __tablename__ = 'users'

    email = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=True)
    uid = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)
    points = Column(Integer, default=0)   # 0 points means user is not created in Stripe
    tier = Column(String(100), default="FREE")  # FREE, PERSONAL, BUSINESS, ENTERPRISE

    processes = relationship("ProcessDB", back_populates="user")


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
class UserPostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://nikhil:neko@192.168.1.99:5445/nikhil"    # Kuro Neko Server
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
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





class ProcessDB(Base):
    __tablename__ = 'processes'

    process_id = Column(String(255), primary_key=True)
    user_email = Column(String(255), ForeignKey('users.email'), nullable=False)
    status = Column(String(255), nullable=False)
    urls = Column(JSON, nullable=False)
    proxies = Column(JSON, nullable=False)
    created_at = Column(String(255), nullable=False)
    parse_text = Column(Integer, default=1)
    parallel_count = Column(Integer, default=1)
    urls_scraped = Column(Integer, default=0)
    urls_failed = Column(Integer, default=0)
    proxies_used = Column(Integer, default=0)
    proxies_failed = Column(Integer, default=0)
    file_path = Column(String(255), nullable=True)
    file_hash = Column(String(255), nullable=True)

    user = relationship("UserDB", back_populates="processes")


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
class ProcessPostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://nikhil:neko@192.168.1.99:5445/nikhil"    # Kuro Neko Server
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, process_id, user_email, status, urls, proxies, created_at, parse_text=1, parallel_count=10):
        try:
            session = self.Session()
            process = ProcessDB(
                process_id=process_id,
                user_email=user_email,
                status=status,
                urls=urls,
                proxies=proxies,
                created_at=created_at,
                parse_text=parse_text,
                parallel_count=parallel_count
            )
            session.add(process)
            session.commit()
            session.close()
            print("ProcessDB record inserted successfully")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def read(self, process_id=None):
        try:
            session = self.Session()
            if process_id:
                process = session.query(ProcessDB).filter_by(process_id=process_id).first()
                if process:
                    return [(process.process_id, process.user_email, process.status, process.urls, process.proxies, process.created_at, process.parse_text, process.parallel_count)]
            else:
                processes = session.query(ProcessDB).all()
                return [(process.process_id, process.user_email, process.status, process.urls, process.proxies, process.created_at, process.parse_text, process.parallel_count) for process in processes]
        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []

    def update(self, process_id, new_data):
        try:
            session = self.Session()
            process = session.query(ProcessDB).filter_by(process_id=process_id).first()
            if process:
                for key, value in new_data.items():
                    setattr(process, key, value)
                session.commit()
                session.close()
                print("ProcessDB record updated successfully")
            else:
                print("ProcessDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def delete(self, process_id):
        try:
            session = self.Session()
            process = session.query(ProcessDB).filter_by(process_id=process_id).first()
            if process:
                session.delete(process)
                session.commit()
                session.close()
                print("ProcessDB record deleted successfully")
            else:
                print("ProcessDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")
