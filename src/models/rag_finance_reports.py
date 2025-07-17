from whoosh.fields import SchemaClass, TEXT, NUMERIC, ID, STORED
from utils.analyser_helper import get_portuguese_analyzer

ANALYZER = get_portuguese_analyzer()


class RAGFinanceReports(SchemaClass):
    id = ID(stored=True)
    doc_type = ID(stored=True)
    month = ID(stored=True, sortable=True)
    year = NUMERIC(stored=True, sortable=True)
    value = NUMERIC(stored=True, sortable=True)
    source = ID(stored=True)
    content = TEXT(stored=True, analyzer=ANALYZER)
    original_data = STORED
