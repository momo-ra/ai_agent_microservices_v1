from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from utils.log import setup_logger
from services.query_service import QueryService

logger = setup_logger(__name__)

async def execute_query_in_database(query: str, session: AsyncSession) -> any:
    
    try:
        # Log the query (truncated for readability)
        query_summary = query[:200] + "..." if len(query) > 200 else query
        logger.info(f'Executing query: {query_summary}')
        
        # Transform the query using QueryService
        # query_service = QueryService()
        # transformed_query = await query_service.transform_query2(query)
        # logger.info(f'Transformed query: {transformed_query}')
        
        # Execute the transformed query
        result = await session.execute(text(query))
        rows = result.fetchall()
        
        # Log information about the results
        logger.info(f'Query returned {len(rows)} rows')
        
        # Validate the first row if results exist
        if rows:
            first_row = rows[0]
            logger.info(f'First row type: {type(first_row)}, length: {len(first_row)}')
            logger.info(f'First row sample: {first_row[0]}, {first_row[1]}, {first_row[2]}')
        
        return rows
    except Exception as e:
        logger.error(f'Error executing query: {e}')
        raise e