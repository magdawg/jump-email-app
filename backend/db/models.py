from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    gmail_accounts = relationship("GmailAccount", back_populates="user")
    categories = relationship("Category", back_populates="user")


class GmailAccount(Base):
    __tablename__ = "gmail_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email = Column(String)
    credentials = Column(Text)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="gmail_accounts")
    emails = relationship("Email", back_populates="gmail_account")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="categories")
    emails = relationship("Email", back_populates="category")


class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True, index=True)
    gmail_account_id = Column(Integer, ForeignKey("gmail_accounts.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    gmail_message_id = Column(String, unique=True)
    subject = Column(String)
    sender = Column(String)
    body = Column(Text)
    summary = Column(Text)
    received_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    gmail_account = relationship("GmailAccount", back_populates="emails")
    category = relationship("Category", back_populates="emails")
