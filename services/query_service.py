# services/query_service.py
import re
import time
from typing import Dict, Any, List, Tuple, Optional
from utils.log import setup_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = setup_logger(__name__)

class QueryService:
    """
    Service for transforming and executing queries
    """
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
    
    async def execute_query(self, db: AsyncSession, query: str, parameters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int, float]:
        """
        Execute a SQL query and return results
        
        Args:
            query: The SQL query to execute
            parameters: Optional query parameters
            
        Returns:
            Tuple of (results, row_count, execution_time_ms)
        """
        logger.info(f"Executing query: {query[:100]}...")
        
        start_time = time.time()
        
        try:
            # Execute the query using provided plant-scoped session
            result = await db.execute(text(query), parameters or {})
            
            # Fetch all rows
            rows = result.fetchall()
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