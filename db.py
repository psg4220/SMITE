import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
from models.base import Base  # Make sure your models are imported here

# Load environment variables
load_dotenv()

# Get the database URL from the .env file
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env file.")

# Create an async engine
engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool, pool_recycle=3600)

# Create a sessionmaker for async sessions
async_session = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)


# Function to get the session
@asynccontextmanager
async def get_session() -> AsyncSession:
    """
    Provide a database session in an async context manager.
    """
    async with async_session() as session:
        yield session
