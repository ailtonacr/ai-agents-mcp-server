import json
import shutil
from pathlib import Path
from whoosh.fields import Schema
from whoosh.index import create_in, open_dir
from infrastructure.logging_config import logger

class RAGManager:
    def create_index(self, index_dir: Path, json_input_path: Path, schema: Schema):
        """
        Creates an index from scratch using the provided schema and JSON data file.

        Args:
            index_dir (Path): Path where the index will be created.
            json_input_path (Path): Path to the JSON file containing the documents to index.
            schema (Schema): Schema definition for the index.

        Raises:
            FileNotFoundError: If the JSON data file does not exist.

        Returns:
            None

        This method removes any existing index at the target location, creates a new index, and populates it with documents from the JSON file.
        """
        if not json_input_path.is_file():
            logger.critical(f'JSON data file not found at: "{json_input_path}"')
            raise FileNotFoundError(f'JSON data file not found at: "{json_input_path}"')

        if index_dir.exists():
            shutil.rmtree(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        ix = create_in(index_dir, schema)
        self._populate_index(ix, json_input_path)
        logger.info(f'Index successfully created at "{index_dir}"')

    def update_index(self, index_dir: Path, json_input_path: Path):
        """
        Adds documents from a JSON file to an existing Whoosh index.

        Args:
            index_dir (Path): Path to the existing Whoosh index directory.
            json_input_path (Path): Path to the JSON file containing the documents to add.

        Raises:
            FileNotFoundError: If the JSON data file or index directory does not exist.

        Returns:
            None

        This method opens the existing index and adds new documents from the JSON file.
        """
        if not json_input_path.is_file():
            logger.critical(f'JSON data file for update not found at: "{json_input_path}"')
            raise FileNotFoundError(f'JSON data file for update not found at: "{json_input_path}"')
        if not index_dir.exists():
            logger.critical(f'Cannot update. The index directory "{index_dir}" does not exist')
            raise FileNotFoundError(f'Cannot update. The index directory "{index_dir}" does not exist')

        ix = open_dir(index_dir)
        self._populate_index(ix, json_input_path, is_update=True)
        logger.info(f'Index at "{index_dir}" successfully updated')

    @staticmethod
    def _populate_index(index_obj, json_input_path: Path, is_update: bool = False):
        """
        Populates or updates a Whoosh index with documents from a JSON file.

        Args:
            index_obj: The Whoosh index object to write to.
            json_input_path (Path): Path to the JSON file containing the documents.
            is_update (bool): If True, updates the index; if False, populates it from scratch.

        Raises:
            Exception: If an error occurs while processing the documents.

        Returns:
            None

        This method reads the documents from the specified JSON file and adds them to the Whoosh index.
        It logs the operation type and the number of documents processed. Commits the changes at the end.
        """
        writer = index_obj.writer()
        with json_input_path.open('r', encoding='utf-8') as f:
            docs = json.load(f)
        try:
            op_type = 'Adding' if is_update else 'Populating with'
            logger.info(f'{op_type} {len(docs)} documents...')
            for doc in docs:
                writer.add_document(original_data=json.dumps(doc), **doc)
            writer.commit()
        except Exception as e:
            logger.critical(f'Error processing documents: {e}')
            writer.cancel()
            raise RuntimeError(f'Error processing documents: {e}') from e
