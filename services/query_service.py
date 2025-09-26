# services/query_service.py
import re
import time
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator
from utils.log import setup_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database import validate_plant_access
from database import get_plant_neo4j_db
from neo4j import AsyncSession as Neo4jAsyncSession
from neo4j.exceptions import SessionError
from tqdm import tqdm

logger = setup_logger(__name__)

class QueryService:
    """
    Service for transforming and executing queries
    """
    
    async def validate_plant_access(self, user_id: int, plant_id: str) -> bool:
        """Validate if user has access to the plant database"""
        try:
            return await validate_plant_access(user_id, plant_id)
        except Exception as e:
            logger.error(f"Error validating plant access: {e}")
            return False
    async def transform_query2(original_query):
        cleaned_query = original_query.strip()
        if cleaned_query.endswith(';'):
            cleaned_query = cleaned_query[:-1]
        
        # إنشاء الاستعلام المحول باستخدام WITH clause
        transformed_query = f"""
    WITH original_query AS (
        {cleaned_query}
    )
    SELECT
        bucket AS timestamp,
        avg_value AS value,
        name AS tag_id
    FROM original_query
    ORDER BY timestamp, tag_id
    """
    
        return transformed_query
    async def transform_query(self, original_query: str, column_mapping: Optional[Dict[str, str]] = None) -> str:
        logger.info("Transforming query") 
        # Default column mapping if none provided
        if not column_mapping:
            column_mapping = {
                "bucket": "timestamp",
                "avg_value": "value", 
                "name": "tag_id"
            }
        
        # Detect query type
        is_time_bucket = "time_bucket" in original_query.lower()
        
        # Clean up the query (remove leading/trailing whitespace and newlines)
        cleaned_query = original_query.strip()
        
        # Wrap in WITH clause
        if is_time_bucket:
            # For time_bucket queries, use the specific column mapping
            select_clause = ", ".join([
                f"{original} AS {new_name}"
                for original, new_name in column_mapping.items()
            ])
            
            transformed_query = f"""
            WITH original_query AS (
                {cleaned_query}
            )
            SELECT
                {select_clause}
            FROM original_query
            ORDER BY {column_mapping.get('bucket', 'timestamp')}, {column_mapping.get('name', 'tag_id')};
            """
        else:
            # For other queries, make a best guess at the structure
            transformed_query = f"""
            WITH original_query AS (
                {cleaned_query}
            )
            SELECT * FROM original_query;
            """
        
        logger.info("Query transformation complete")
        return transformed_query
    
    async def execute_query(self, db: AsyncSession, query: str, parameters: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None, plant_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Execute a SQL query and return results
        
        Args:
            query: The SQL query to execute
            parameters: Optional query parameters
            user_id: User ID for access validation
            plant_id: Plant ID for access validation
            
        Returns:
            Tuple of (results, row_count, execution_time_ms)
        """
        logger.info(f"Executing query: {query[:100]}...")
        
        # Validate plant access if user_id and plant_id are provided
        if user_id and plant_id:
            if not await self.validate_plant_access(user_id, plant_id):
                raise PermissionError(f"User {user_id} does not have access to plant {plant_id}")
        
        start_time = time.time()
        
        try:
            # Execute the query using provided plant-scoped session
            result = await db.execute(text(query), parameters or {})
            
            # Fetch all rows
            rows = result.fetchall()
            print("==============================")
            print(rows)
            print("==============================")
            row_count = len(rows)
            
            # Convert to list of dicts for easier JSON serialization
            if rows and hasattr(result, 'keys'):
                column_names = result.keys()
                results = [dict(zip(column_names, row)) for row in rows]
            else:
                # Fallback if column names can't be determined
                results = [{"column_" + str(i): value for i, value in enumerate(row)} for row in rows]
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            logger.info(f"Query executed successfully. {row_count} rows returned in {execution_time:.2f}ms")
            
            return results, row_count, execution_time
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a SQL query to extract key information
        
        Args:
            query: The SQL query to analyze
            
        Returns:
            Dictionary with analysis data like column names, filters, etc.
        """
        analysis = {
            "query_type": "unknown",
            "tables": [],
            "columns": [],
            "filters": {},
            "time_range": None,
            "time_bucket": None,
            "tags": []
        }
        
        # Simple detection of query type
        if "time_bucket" in query.lower():
            analysis["query_type"] = "time_bucket"
            
            # Try to extract the time bucket interval
            bucket_match = re.search(r"time_bucket\(\s*'([^']+)'", query, re.IGNORECASE)
            if bucket_match:
                analysis["time_bucket"] = bucket_match.group(1)
        
        # Extract tables
        from_match = re.search(r"FROM\s+([^\s]+)", query, re.IGNORECASE)
        if from_match:
            analysis["tables"].append(from_match.group(1))
        
        # Extract JOIN tables
        join_matches = re.findall(r"JOIN\s+([^\s]+)", query, re.IGNORECASE)
        if join_matches:
            analysis["tables"].extend(join_matches)
        
        # Extract date range
        timestamp_matches = re.findall(r"timestamp\s+[><]=?\s+'([^']+)'", query, re.IGNORECASE)
        if len(timestamp_matches) >= 2:
            analysis["time_range"] = {
                "start": timestamp_matches[0],
                "end": timestamp_matches[1]
            }
        
        # Extract tags
        tag_matches = re.findall(r"lower\('([^']+)'\)", query, re.IGNORECASE)
        if tag_matches:
            analysis["tags"] = tag_matches
        
        return analysis


##======================================================
## NEO4J QUERY SERVICE
##======================================================

class KnowledgeGraph:
    """
    Async Knowledge Graph service for plant-specific Neo4j operations
    """
    
    def __init__(self, plant_id: str):
        self.plant_id = plant_id
        # TODO: controllare su tutti i metodi che sia supportati labels multipli e che parta un eccezzione se non ci sono label
        self.ENTITY_QUERY_CONSTRUCTOR = "MERGE (:{TYPE} {ATTRIBUTES})"
        self.RELATIONSHIP_QUERY_CONSTRUCTOR = """
        MATCH (x:{X_TYPE} {{name_id :"{X_ID}"}}),(y:{Y_TYPE} {{name_id: "{Y_ID}"}})
        MERGE (x)-[:{REL_TYPE} {REL_ATTR}]->(y)
        """
        logger.info(f"KnowledgeGraph initialized for plant {plant_id}")

    async def get_session(self) -> AsyncGenerator[Neo4jAsyncSession, Any]:
        """Get a plant-specific Neo4j database session"""
        async for session in get_plant_neo4j_db(self.plant_id):
            yield session

    # TODO: sarebbe da settare thread-safetiness ma nel pratico la scrittura viene fatta solo da backend quindi non è necesaria
    async def write_queries(self, queries: List[str], session: Neo4jAsyncSession, batch_size: int = 500) -> int:
        """
        Execute write queries in batches using async Neo4j session
        
        Args:
            queries: List of Cypher queries to execute
            session: Async Neo4j session
            batch_size: Number of queries to process in each batch
            
        Returns:
            Total number of queries executed
        """
        async def write_tx_queries(tx, queries: List[str]):
            for query in tqdm(queries, desc="batch", leave=False):
                # Check if there are multiple queries
                query_parts = query.split(";")
                for q in query_parts:
                    q = q.strip()
                    if q != "":
                        await tx.run(q)
        
        try:
            # For transactions bigger than 1000 entries it's better to commit them each 1k units, otherwise too much memory is used
            batches = 1 + (len(queries) // batch_size)
            tot = 0
            for i in tqdm(range(batches), desc="batch_number"):
                start = i * batch_size
                end = (i + 1) * batch_size if i < batches - 1 else len(queries)
                batch = queries[start:end]
                await session.execute_write(write_tx_queries, batch)
                tot += len(batch)
            
            logger.info(f"Successfully executed {tot} queries")
            return tot
            
        except SessionError as e:
            logger.error(f'While executing some queries as a transaction, an error occurred.\nQueries:\n{queries}\n\n{e}')
            raise
        except Exception as e:
            logger.error(f"Some errors with Neo4j database communication occurred.\n{e}")
            raise
        
    # Already thread safe
    async def read_queries(self, queries: List[str], session: Neo4jAsyncSession) -> List[List[dict]]:
        """
        Execute a list of read queries using async Neo4j session.
        
        Args:
            queries: List of Cypher queries to execute
            session: Async Neo4j session
            
        Returns:
            List of query results (each result is a list of dictionaries).
            Each query with no result will return [] as its result -> if 3 queries get no result, you will get [[][][]]
            If some errors occur, the method returns [[]] as if you had a query with no results.
        """
        async def read_tx_queries(tx, queries: List[str]):
            result = []
            for query in queries:
                query_result = await tx.run(query)
                result.append(await query_result.data())
            return result
        
        try:
            res = await session.execute_read(read_tx_queries, queries)
            return res
        except SessionError as e:
            logger.error(f'While executing some queries as a transaction, an error occurred.\nQueries:\n{queries}\n\n{e}')
        except Exception as e:
            logger.error(f"Some errors with Neo4j database communication occurred.\n{e}")
        # If some exception is captured, return a list containing a void result for a query
        return [[]]

    async def read_query(self, query: str, session: Neo4jAsyncSession) -> List[dict]:
        """
        Execute a single query using async Neo4j session.
        
        Args:
            query: Cypher query to execute
            session: Async Neo4j session
            
        Returns:
            List of dictionaries each representing a retrieved entry from the database.
            Returns [] if there is no match.
        """
        results = await self.read_queries([query], session)
        return results[0] if results else []

    
