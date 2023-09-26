from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TEXT, BOOLEAN
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from src.utils.base.basic import retry
import json

Base = declarative_base()


class UserDB(Base):
    __tablename__ = 'users'

    email = Column(String(255), primary_key=True)
    uid = Column(String(255), nullable=False)
    points = Column(Integer, default=0)
    plan = Column(String(100), default="FREE")
    parallel_count = Column(Integer, default=1)
    config = Column(TEXT, default="")

    jobs = relationship("JobDB", back_populates="user")
    logs = relationship("LogDB", back_populates="user")


class JobDB(Base):
    __tablename__ = 'jobs'

    job_id = Column(String(255), primary_key=True)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    status = Column(String(255), nullable=False)
    urls = Column(TEXT, nullable=False)
    proxies = Column(TEXT, nullable=False)
    created_at = Column(String(255), nullable=False)
    do_parsing = Column(BOOLEAN, default=True)
    parallel_count = Column(Integer, default=1)
    urls_scraped = Column(TEXT, default="")
    urls_failed = Column(TEXT, default="")
    proxies_used = Column(TEXT, default="")
    proxies_failed = Column(TEXT, default="")
    points_used = Column(Integer, default=0)
    zip_file_path = Column(String(255), nullable=True)
    zip_file_hash = Column(String(255), nullable=True)

    user = relationship("UserDB", back_populates="jobs")


class LogDB(Base):
    __tablename__ = 'logs'

    log_id = Column(Integer, primary_key=True)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    log_data = Column(TEXT, nullable=False)
    created_at = Column(String(255), nullable=False)

    user = relationship("UserDB", back_populates="logs")



@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
class UserPostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://nikhil:neko@192.168.1.99:5445/nikhil"    # Kuro Neko Server
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, email, uid, points=0, plan="FREE", parallel_count=1, config=""):
        try:
            session = self.Session()
            user = UserDB(email=email, uid=uid, points=points, plan=plan, parallel_count=parallel_count, config=config)
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
                    return {
                        "email": user.email,
                        "uid": user.uid,
                        "points": user.points,
                        "plan": user.plan,
                        "parallel_count": user.parallel_count,
                        "config": user.config
                    }
            else:
                users = session.query(UserDB).all()
                return [{
                    "email": user.email,
                    "uid": user.uid,
                    "points": user.points,
                    "plan": user.plan,
                    "parallel_count": user.parallel_count,
                    "config": user.config
                } for user in users]

        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return {}

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


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
class JobPostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://nikhil:neko@192.168.1.99:5445/nikhil"    # Kuro Neko Server
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, job_id, email, status, urls, proxies, created_at, do_parsing=True, parallel_count=1):
        try:
            session = self.Session()
            process = JobDB(
                job_id=job_id,
                email=email,
                status=status,
                urls=urls,
                proxies=proxies,
                created_at=created_at,
                do_parsing=do_parsing,
                parallel_count=parallel_count
            )
            session.add(process)
            session.commit()
            session.close()
            print("JobDB record inserted successfully")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def read(self, job_id=None):
        try:
            session = self.Session()
            if job_id:
                job = session.query(JobDB).filter_by(job_id=job_id).first()
                if job:
                    return {
                        "job_id": job.job_id,
                        "email": job.email,
                        "status": job.status,
                        "urls": self._parse_list_string(input_string=job.urls),
                        "proxies": self._parse_list_string(input_string=job.proxies),
                        "created_at": job.created_at,
                        "do_parsing": job.do_parsing,
                        "parallel_count": job.parallel_count,
                        "urls_scraped": self._parse_list_string(input_string=job.urls_scraped),
                        "urls_failed": self._parse_list_string(input_string=job.urls_failed),
                        "proxies_used": self._parse_list_string(input_string=job.proxies_used),
                        "proxies_failed": self._parse_list_string(input_string=job.proxies_failed),
                        "points_used": job.points_used,
                        "zip_file_path": job.zip_file_path,
                        "zip_file_hash": job.zip_file_hash,
                    }
            else:
                jobs = session.query(JobDB).all()
                return [{
                    "job_id": job.job_id,
                    "email": job.email,
                    "status": job.status,
                    "urls": self._parse_list_string(input_string=job.urls),
                    "proxies": self._parse_list_string(input_string=job.proxies),
                    "created_at": job.created_at,
                    "do_parsing": job.do_parsing,
                    "parallel_count": job.parallel_count,
                    "urls_scraped": self._parse_list_string(input_string=job.urls_scraped),
                    "urls_failed": self._parse_list_string(input_string=job.urls_failed),
                    "proxies_used": self._parse_list_string(input_string=job.proxies_used),
                    "proxies_failed": self._parse_list_string(input_string=job.proxies_failed),
                    "points_used": job.points_used,
                    "zip_file_path": job.zip_file_path,
                    "zip_file_hash": job.zip_file_hash,
                } for job in jobs]

        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []

    def update(self, job_id, new_data):
        try:
            session = self.Session()
            job = session.query(JobDB).filter_by(job_id=job_id).first()
            if job:
                # Update process attributes as needed
                for key, value in new_data.items():
                    setattr(job, key, value)
                session.commit()
                session.close()
                print("JobDB record updated successfully")
            else:
                print("JobDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def delete(self, job_id):
        try:
            session = self.Session()
            job = session.query(JobDB).filter_by(job_id=job_id).first()
            if job:
                session.delete(job)
                session.commit()
                session.close()
                print("JobDB record deleted successfully")
            else:
                print("JobDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")


    def _parse_list_string(self, input_string: str) -> list:
        if input_string:
            parsed_str = json.loads(input_string)
        else:
            parsed_str = []
        return parsed_str

    def filter_jobs(self, filters):
        try:
            session = self.Session()
            query = session.query(JobDB)

            switcher = {
                "job_id": query.filter_by(job_id=filters.get("job_id")),
                "email": query.filter_by(email=filters.get("email")),
                "status": query.filter_by(status=filters.get("status")),
                "created_at": query.filter_by(created_at=filters.get("created_at")),
                "do_parsing": query.filter_by(do_parsing=filters.get("do_parsing")),
                "parallel_count": query.filter_by(parallel_count=filters.get("parallel_count")),
                "points_used": query.filter_by(points_used=filters.get("points_used")),
                "zip_file_path": query.filter_by(zip_file_path=filters.get("zip_file_path")),
                "zip_file_hash": query.filter_by(zip_file_hash=filters.get("zip_file_hash")),
            }
            query = switcher.get(filters.get("filter_by"), "Invalid filter_by")

            if query != "Invalid filter_by":
                jobs = query.all()
                return [{
                    "job_id": job.job_id,
                    "email": job.email,
                    "status": job.status,
                    "urls": self._parse_list_string(input_string=job.urls),
                    "proxies": self._parse_list_string(input_string=job.proxies),
                    "created_at": job.created_at,
                    "do_parsing": job.do_parsing,
                    "parallel_count": job.parallel_count,
                    "urls_scraped": self._parse_list_string(input_string=job.urls_scraped),
                    "urls_failed": self._parse_list_string(input_string=job.urls_failed),
                    "proxies_used": self._parse_list_string(input_string=job.proxies_used),
                    "proxies_failed": self._parse_list_string(input_string=job.proxies_failed),
                    "points_used": job.points_used,
                    "zip_file_path": job.zip_file_path,
                    "zip_file_hash": job.zip_file_hash,
                } for job in jobs]
            else:
                return []
        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
class LogPostgreSQLCRUD:
    def __init__(self):
        db_url = "postgresql://nikhil:neko@localhost:5445/nikhil"    # Kuro Neko Server
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, email, log_data, created_at):
        try:
            session = self.Session()
            log = LogDB(email=email, log_data=log_data, created_at=created_at)
            session.add(log)
            session.commit()
            session.close()
            print("LogDB record inserted successfully")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def read(self, log_id=None):
        try:
            session = self.Session()
            if log_id:
                log = session.query(LogDB).filter_by(log_id=log_id).first()
                if log:
                    return {
                        "log_id": log.log_id,
                        "email": log.email,
                        "log_data": log.log_data,
                        "created_at": log.created_at,
                    }
            else:
                logs = session.query(LogDB).all()
                return [{
                    "log_id": log.log_id,
                    "email": log.email,
                    "log_data": log.log_data,
                    "created_at": log.created_at,
                } for log in logs]

        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []
        
    def update(self, log_id, new_data):
        try:
            session = self.Session()
            log = session.query(LogDB).filter_by(log_id=log_id).first()
            if log:
                # Update process attributes as needed
                for key, value in new_data.items():
                    setattr(log, key, value)
                session.commit()
                session.close()
                print("LogDB record updated successfully")
            else:
                print("LogDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def delete(self, log_id):
        try:
            session = self.Session()
            log = session.query(LogDB).filter_by(log_id=log_id).first()
            if log:
                session.delete(log)
                session.commit()
                session.close()
                print("LogDB record deleted successfully")
            else:
                print("LogDB not found")
        except SQLAlchemyError as e:
            print(f"Error: {e}")

    def filter_logs(self, filters):
        try:
            session = self.Session()
            query = session.query(LogDB)

            switcher = {
                "log_id": query.filter_by(log_id=filters["log_id"]),
                "email": query.filter_by(email=filters["email"]),
                "created_at": query.filter_by(created_at=filters["created_at"]),
            }

            query = switcher.get(filters["filter_by"], "Invalid filter_by")

            if query != "Invalid filter_by":
                logs = query.all()
                return [{
                    "log_id": log.log_id,
                    "email": log.email,
                    "log_data": log.log_data,
                    "created_at": log.created_at,
                } for log in logs]
            else:
                return []
        except SQLAlchemyError as e:
            print(f"Error: {e}")
            return []

