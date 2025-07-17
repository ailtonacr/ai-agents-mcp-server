import nltk
import time
from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter, Analyzer
from nltk.corpus import stopwords
from infrastructure.logging_config import logger

_NLTK_STOPWORDS_CHECKED = False

def _nltk_stopwords_check():
    """
    Checks if the NLTK 'stopwords' package is available.
    If not, attempts to download it automatically.
    This ensures that the stopwords resource is present for text analysis tasks.
    Logs the process and any errors encountered.
    Raises an exception if the download fails.
    """
    global _NLTK_STOPWORDS_CHECKED
    if _NLTK_STOPWORDS_CHECKED:
        return

    try:
        stopwords.words('portuguese')
        logger.info('NLTK "stopwords" package is already available.')
    except LookupError:
        logger.warning('NLTK "stopwords" package not found. Attempting to download...')
        try:
            nltk.download('stopwords')
            logger.info('Successfully downloaded the "stopwords" package.')
            stopwords.words('portuguese')
            _NLTK_STOPWORDS_CHECKED = True
        except Exception as e:
            logger.critical(f'Failed to download NLTK data. Text analyzer may not work properly. Error: {e}')
            raise RuntimeError(f'Failed to download NLTK data. Text analyzer may not work properly. Error: {e}')

def get_portuguese_analyzer() -> Analyzer:
    """
    Creates and returns a default Whoosh analyzer configured for Portuguese texts.
    Ensures that the necessary NLTK packages are downloaded.
    The analyzer tokenizes text, converts it to lowercase, and removes stopwords.

    Returns:
        Analyzer: A Whoosh analyzer instance for Portuguese.
    """
    _nltk_stopwords_check()

    try:
        pt_stop_words = frozenset(stopwords.words('portuguese'))
    except LookupError:
        logger.warning('Trying again after 10 seconds...')
        time.sleep(10)
        try:
            _nltk_stopwords_check()
            pt_stop_words = frozenset(stopwords.words('portuguese'))
        except LookupError as e:
            raise RuntimeError(f'Error when trying to execute the fallback: {e}')
    return RegexTokenizer() | LowercaseFilter() | StopFilter(pt_stop_words)
