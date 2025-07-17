from pathlib import Path
import sys
import json

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from infrastructure.logging_config import logger
from services.finance_report_rag_searcher import FinanceReportRAGSearcher

INDEX_DIR = ROOT_DIR / "data" / "indexes" / "finance_reports"
try:
    SEARCHER = FinanceReportRAGSearcher(index_dir=INDEX_DIR)
except Exception as e:
    SEARCHER = None
    logger.critical(f'could not initialize the rag searcher: {e}')


def rag_finance_report_search(query: str, filter_by: dict) -> str:
    """
    Executes a search in the ACR Tech finance RAG system.

    Args:
        query (str): The user's search query string.
        filter_by (dict): Dictionary with filter parameters for the search.

    Returns:
        str: A JSON string with the search results or an error message.
    """
    if not SEARCHER:
        return json.dumps({"status": "error", "message": "Search system not available."})

    logger.info(f'Forwarding search to RAG instance: query="{query}", filters="{filter_by}"')

    result_dict = SEARCHER.search(query_string=query, filter_by=filter_by)
    return json.dumps(result_dict, ensure_ascii=False)


def get_finance_report_filters() -> str:
    """
    Returns a list of all available filters and values for the finance RAG system.

    This function queries the RAG searcher for its available filters and formats
    the response as a JSON string.

    Returns:
        str: A JSON string with the available filters or an error message.
    """
    if not SEARCHER:
        return json.dumps({"status": "error", "message": "Search system not available."})

    try:
        available_values = SEARCHER.get_available_filters()

        response = {"status": "success", "available_filters": available_values}
        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        logger.error(f'Error discovering filters: {e}')
        error_response = {"status": "error", "message": str(e)}
        return json.dumps(error_response)
