import json
from pathlib import Path
from typing import Any, List

from whoosh.index import open_dir, Index
from whoosh.query import Term, Or, And
from whoosh import scoring
from whoosh.qparser import MultifieldParser, OrGroup, AndGroup

from infrastructure.logging_config import logger


class BaseRAGSearcher:
    def __init__(self, index_dir: Path, search_fields: list[str], default_operator: str = "OR"):
        """
        Initializes the generic searcher.

        Args:
            index_dir (Path): Path to the Whoosh index directory.
            search_fields (List[str]): List of fields where free text search will be applied.
                                      E.g.: ["content", "source"]
            default_operator (str): Default operator for text search ("OR" or "AND").
        """
        if not index_dir.is_dir():
            logger.critical(f'Whoosh index directory not found: "{index_dir}"')
            raise FileNotFoundError(f'Whoosh index directory not found: "{index_dir}"')

        self.ix: Index = open_dir(index_dir)

        group_op = OrGroup if default_operator.upper() == "OR" else AndGroup
        self.parser = MultifieldParser(search_fields, schema=self.ix.schema, group=group_op)

        logger.info(f'{self.__class__.__name__} initialized for "{index_dir}". Search fields: {search_fields}.')

    def search(self, query_string: str, top_k: int = 5, filter_by: dict[str, Any] = None) -> dict:
        """
        Executes a complete search, combining text and filters, and returns a structured dictionary.

        Args:
            query_string (str): The user's search string.
            top_k (int): The maximum number of results.
            filter_by (dict[str, Any], optional): Dictionary for exact filters.

        Returns:
            dict: A dictionary with the status and results of the search.
        """
        logger.info(f'Preparing query for: "{query_string}" with filter "{filter_by}"')

        main_query = self.parser.parse(query_string)

        final_query = main_query
        if filter_by:
            filter_queries = []
            for field, value_or_list in filter_by.items():
                if isinstance(value_or_list, list) and value_or_list:
                    term_queries = [Term(field, v) for v in value_or_list]
                    filter_queries.append(Or(term_queries))
                elif not isinstance(value_or_list, list):
                    filter_queries.append(Term(field, value_or_list))

            if filter_queries:
                final_query = And([main_query] + filter_queries)

        logger.info(f'Final query built: {final_query}')

        try:
            with self.ix.searcher(weighting=scoring.BM25F()) as searcher:
                results = searcher.search(final_query, limit=top_k)

                if not results:
                    return {"status": "success", "count": 0, "results": []}

                found_docs = [json.loads(hit['original_data']) for hit in results]

                return {
                    "status": "success",
                    "count": len(found_docs),
                    "results": found_docs
                }
        except Exception as e:
            logger.error(f'Error executing Whoosh search: {e}')
            return {"status": "error", "message": "Failed to execute search in the database."}

    def discover_filterable_values(self, fields_to_inspect: list[str]) -> dict:
        """
        Inspects the index to find all unique values for a list of fields.

        Args:
            fields_to_inspect (list[str]): List of field names to inspect in the index schema.

        Returns:
            dict: A dictionary where each key is a field name and the value is a sorted list of unique values found for that field in the index.

        This method is useful for dynamically discovering which values are available for filtering in search interfaces or APIs.
        If a field is not present in the schema, it will be ignored and a warning will be logged.
        """
        logger.info(f'Starting value discovery for fields: {fields_to_inspect}')

        filter_options = {}
        with self.ix.reader() as reader:
            for field_name in fields_to_inspect:
                if field_name not in reader.schema:
                    logger.warning(f'The field "{field_name}" was not found in the schema and will be ignored.')
                    continue
                try:
                    field_obj = reader.schema[field_name]
                    values = [field_obj.from_bytes(term_bytes) for term_bytes in reader.lexicon(field_name)]
                    filter_options[field_name] = sorted(list(set(values)))
                except Exception as e:
                    logger.error(f'Could not process the lexicon for field "{field_name}": {e}')
                    filter_options[field_name] = []

        logger.info(f'Filter values found: {filter_options}')
        return filter_options
