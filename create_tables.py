import asyncio
from models.base import Base  # Import Base from your base file
from db import engine  # Import your engine from the db module
from sqlalchemy.ext.asyncio import AsyncSession

# Create tables asynchronously
async def create_tables():
    # Use the engine to run create_all synchronously in an async context
    async with engine.begin() as conn:  # engine.begin() is used for transaction
        await conn.run_sync(Base.metadata.create_all)  # Run create_all synchronously

# Run the function asynchronously
if __name__ == "__main__":
    asyncio.run(create_tables())
