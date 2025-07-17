from pathlib import Path
from .base_rag_searcher import BaseRAGSearcher
from infrastructure.logging_config import logger


ROOT_DIR = Path(__file__).parent.parent

FINANCE_REPORTS = ROOT_DIR / "data" / "indexes" / "finance_reports"

class FinanceReportRAGSearcher(BaseRAGSearcher):
    """
    Specialized searcher for financial reports.
    Defines which fields are searchable and which are filterable.
    """
    FILTERABLE_FIELDS = ['doc_type', 'month', 'year', 'source']

    def __init__(self, index_dir: Path):
        searchable_fields = ["content", "source"]

        super().__init__(
            index_dir=index_dir,
            search_fields=searchable_fields,
            default_operator="OR"
        )
        logger.info(f'{self.__class__.__name__} configured and ready.')

    def search(self, query_string: str, top_k: int = 3, filter_by: dict = None) -> dict:
        """
        Executes a search using the inherited logic from the base class.

        Args:
            query_string (str): The user's search string.
                                Example: "highest revenue".
            top_k (int): The maximum number of results to return.
            filter_by (dict, optional): Dictionary for exact field filters.
                                        Default is None.
                                        Example: {'year': 2024, 'type': 'monthly_revenue'}

        Returns:
            dict: A structured dictionary with the status and search results.
                  Example: {"status": "success", "count": 1, "results": [...]}
        """
        return super().search(query_string, top_k, filter_by)

    def get_available_filters(self) -> dict:
        """
        Returns the unique values for the filterable fields defined in this class.

        Returns:
            dict: A dictionary where the keys are the names of the filterable fields and the values are lists of unique values found for each field.
        """
        logger.info(f'Discovering values for the defined finance fields: {self.FILTERABLE_FIELDS}')
        return self.discover_filterable_values(self.FILTERABLE_FIELDS)
