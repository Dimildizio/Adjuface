from datetime import datetime, date
from sqlalchemy import Column, Integer, String, TIMESTAMP, Date, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine

from bot.handlers.constants import ASYNC_DB_URL


Base = declarative_base()
async_engine = create_async_engine(ASYNC_DB_URL, echo=True)


class PremiumPurchase(Base):
    __tablename__: str = 'premium_purchases'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purchase_date = Column(Date, default=date.today)
    expiration_date = Column(Date)
    targets_increment = Column(Integer, default=10)
    request_increment = Column(Integer, default=100)

    user = relationship("User", back_populates='premium_purchases')


class User(Base):
    __tablename__: str = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    mode = Column(Integer, default=1)
    receive_target_flag = Column(Integer, default=0)
    status = Column(String, default='free')
    requests_left = Column(Integer, default=10)
    targets_left = Column(Integer, default=0)
    last_photo_sent_timestamp = Column(TIMESTAMP, default=datetime.now())
    premium_expiration = Column(Date, nullable=True)

    messages = relationship("Message", back_populates="user")
    image_names = relationship("ImageName", back_populates="user")
    premium_purchases = relationship("PremiumPurchase", back_populates="user", order_by='PremiumPurchase.purchase_date')
    payments = relationship("Payment", back_populates="user")


class Message(Base):
    __tablename__: str = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    text_data = Column(String)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="messages")


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    operation_id = Column(String)
    payment_datetime = Column(TIMESTAMP, default=datetime.now())

    user = relationship("User", back_populates="payments")


class ImageName(Base):
    __tablename__: str = 'image_names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    input_image_name = Column(String)
    output_image_names = Column(String)
    timestamp = Column(TIMESTAMP, default=datetime.now())

    user = relationship("User", back_populates="image_names")


class SchedulerLog(Base):
    __tablename__ = 'scheduler_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String, nullable=False)
    run_datetime = Column(TIMESTAMP, server_default=func.now())
    status = Column(String, nullable=False)
    details = Column(String, nullable=True)

    def __repr__(self):
        return f"<SchedulerLog(job_name='{self.job_name}', run_datetime='{self.run_datetime}', " \
               f"status='{self.status}', details='{self.details}')>"


class ErrorLog(Base):
    __tablename__ = 'error_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    error_message = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    details = Column(String, nullable=True)


async def initialize_database() -> None:
    """"
    Initialize and create the tables in the database asynchronously
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
