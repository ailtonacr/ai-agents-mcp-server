from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from models.rag_finance_reports import RAGFinanceReports
from services.rag_manager import RAGManager
from infrastructure.logging_config import logger

if __name__ == "__main__":
    DATA_DIR = ROOT_DIR / "data"

    YOUR_DOMAIN = Path(__file__).parent.name

    NEW_DATA_JSON_PATH = DATA_DIR / "src" / YOUR_DOMAIN / "faturamento_acr_tech_2024.json"

    INDEX_DIR_PATH = DATA_DIR / "indexes" / YOUR_DOMAIN

    logger.info(f'Starting "{YOUR_DOMAIN}" index update')

    try:
        finance_schema = RAGFinanceReports()

        rag_manager = RAGManager()

        rag_manager.update_index(
            index_dir=INDEX_DIR_PATH,
            json_input_path=NEW_DATA_JSON_PATH
        )

        logger.info(f'{YOUR_DOMAIN} index updated successfully')

    except FileNotFoundError as e:
        logger.error(f'File not found: {e}')
    except Exception as e:
        logger.error(f'Failed to update index: {e}')
