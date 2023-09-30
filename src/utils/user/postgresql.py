from src.utils.base.libraries import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey,
    declarative_base,
    TEXT,
    BOOLEAN,
    sessionmaker,
    relationship,
    SQLAlchemyError,
    QueuePool,
    json,
    logging
)
from src.utils.base.basic import retry, Error
from src.utils.base.constants import POSTGRES_DB_URL


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


class JobDB(Base):
    __tablename__ = 'jobs'

    job_uid = Column(String(255), primary_key=True)
    email = Column(String(255), ForeignKey('users.email'), nullable=False)
    status = Column(String(255), nullable=False)        # Status of the job
    profile_name = Column(String(255), nullable=False)  # The profile name that was used to create the job
    created_at = Column(String(255), nullable=False)    # When the job was created
    job_name = Column(String(255), nullable=True)       # User can add a name to the job if needed
    job_description = Column(TEXT, nullable=True)       # User can add a description to the job if needed
    zip_file_url = Column(TEXT, nullable=True, default="Still processing")  # The URL of the zip file, if the job is completed

    user = relationship("UserDB", back_populates="jobs")



@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2 )
class UserPostgreSQLCRUD:
    def __init__(self):
        db_url = POSTGRES_DB_URL
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
            return True
        except SQLAlchemyError as e:
            logging.error(f"Error while creating user: {e}")
            return Error(code=500, message="Error while creating user in UserDB")

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
            logging.error(f"Error while reading user: {e}")
            return Error(code=500, message="Error while reading user from UserDB")

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
                return True
        except SQLAlchemyError as e:
            logging.error(f"Error while updating user: {e}")
            return Error(code=500, message="Error while updating user in UserDB")

    def delete(self, email):
        try:
            session = self.Session()
            user = session.query(UserDB).filter_by(email=email).first()
            if user:
                session.delete(user)
                session.commit()
                session.close()
                return True
            else:
                logging.error(f"User not found while deleting user in UserDB with email: {email}")
                return Error(code=404, message="User not found while deleting user in UserDB")
        except SQLAlchemyError as e:
            logging.error(f"Error while deleting user: {e}")
            return Error(code=500, message="Error while deleting user from UserDB")

    def update_config(self, email, new_config: dict):
        """Update config in UserDB, without overwriting the existing config"""
        try:
            session = self.Session()
            user = session.query(UserDB).filter_by(email=email).first()
            if user:
                old_config = json.loads(user.config)
                for key, value in new_config.items():
                    old_config[key] = value
                user.config = json.dumps(old_config)
                session.commit()
                session.close()
                return True
            else:
                logging.error(f"User not found while updating config in UserDB with email: {email}")
                return Error(code=404, message="User not found while updating config in UserDB")
        except SQLAlchemyError as e:
            logging.error(f"Error while updating config: {e}")
            return Error(code=500, message="Error while updating config in UserDB")


@retry(Exception, total_tries=5, initial_wait=1, backoff_factor=2)
class JobPostgreSQLCRUD:
    def __init__(self):
        db_url = POSTGRES_DB_URL
        self.engine = create_engine(db_url, poolclass=QueuePool, pool_size=10, max_overflow=20)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create(self, job_uid, email, status, profile_name, created_at, job_name="", job_description="", zip_file_url=""):
        try:
            session = self.Session()
            process = JobDB(
                job_uid=job_uid,
                email=email,
                status=status,
                profile_name=profile_name,
                created_at=created_at,
                job_name=job_name,
                job_description=job_description,
                zip_file_url=zip_file_url
            )
            session.add(process)
            session.commit()
            session.close()
            return True
        except SQLAlchemyError as e:
            logging.error(f"Error while creating job: {e}")
            return Error(code=500, message="Error while creating job in JobDB")

    def read(self, job_uid=None) -> dict | list:
        try:
            session = self.Session()
            if job_uid:
                job = session.query(JobDB).filter_by(job_uid=job_uid).first()
                if job:
                    return {
                        "job_uid": job.job_uid,
                        "email": job.email,
                        "status": job.status,
                        "created_at": job.created_at,
                        "job_name": job.job_name,
                        "job_description": job.job_description,
                        "zip_file_url": job.zip_file_url
                    }
            else:
                jobs = session.query(JobDB).all()
                return [{
                    "job_uid": job.job_uid,
                    "email": job.email,
                    "status": job.status,
                    "created_at": job.created_at,
                    "job_name": job.job_name,
                    "job_description": job.job_description,
                    "zip_file_url": job.zip_file_url
                } for job in jobs]

        except SQLAlchemyError as e:
            logging.error(f"Error while reading job: {e}")
            return Error(code=500, message="Error while reading job from JobDB")

    def update(self, job_uid: str, new_data: dict) -> bool:
        try:
            session = self.Session()
            job = session.query(JobDB).filter_by(job_uid=job_uid).first()
            if job:
                # Update process attributes as needed
                for key, value in new_data.items():
                    setattr(job, key, value)
                session.commit()
                session.close()
                return True
            else:
                logging.error(f"Job not found while updating job in JobDB with job_uid: {job_uid}")
                return Error(code=404, message="Job not found while updating job in JobDB")
        except SQLAlchemyError as e:
            logging.error(f"Error while updating job: {e}")
            return Error(code=500, message="Error while updating job in JobDB")

    def delete(self, job_uid: str) -> bool:
        try:
            session = self.Session()
            job = session.query(JobDB).filter_by(job_uid=job_uid).first()
            if job:
                session.delete(job)
                session.commit()
                session.close()
                return True
            else:
                logging.error(f"Job not found while deleting job in JobDB with job_uid: {job_uid}")
                return Error(code=404, message="Job not found while deleting job in JobDB")
        except SQLAlchemyError as e:
            logging.error(f"Error while deleting job: {e}")
            return Error(code=500, message="Error while deleting job from JobDB")

    def filter_by_email(self, email: str) -> list:
        try:
            session = self.Session()
            jobs = session.query(JobDB).filter_by(email=email).all()
            return [{
                "job_uid": job.job_uid,
                "email": job.email,
                "status": job.status,
                "created_at": job.created_at,
                "job_name": job.job_name,
                "job_description": job.job_description,
                "zip_file_url": job.zip_file_url
            } for job in jobs]
        except SQLAlchemyError as e:
            logging.error(f"Error while filtering job by email: {e}")
            return Error(code=500, message="Error while filtering job by email from JobDB")

