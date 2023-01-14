import os

from flask import Flask
from sqlalchemy import ForeignKey, Column, Integer, Text
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import relationship
from setup import app_config

Base = declarative_base()


def create_app(app_config=app_config):
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(app_config)
    return app


url = URL.create(
    drivername="postgresql",
    username=os.environ.get("DB_USERNAME"),
    password=os.environ.get("DB_PASSWORD"),
    host=os.environ.get("DB_HOST"),
    database=os.environ.get("DATABASE")
)


def get_db_connection(url=url):
    engine = create_engine(url, echo=True)
    return engine.connect(), engine


def set_up_db(connection, engine):
    connection.execute("DROP SCHEMA public CASCADE;"
                       "CREATE SCHEMA public;"
                       "GRANT ALL ON SCHEMA public TO postgres;"
                       "GRANT ALL ON SCHEMA public TO public;")

    Base.metadata.create_all(engine)
    session_maker = sessionmaker(bind=engine)
    return session_maker()


class Author(Base):
    __tablename__ = "authors"
    id = Column(Text, primary_key=True)
    nickname = Column(Text)
    articles = relationship("Article")
    reviews = relationship("Review")


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    content = Column(Text)
    author_id = Column(Text, ForeignKey("authors.id"))
    a_reviews = relationship("Review")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    author_id = Column(Text, ForeignKey("authors.id"))
    article_id = Column(Integer, ForeignKey("articles.id"))
