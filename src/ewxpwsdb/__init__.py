import logging
from .logging_config import setup_logging

# Configure logging for the package
setup_logging()

# Define the package version
__version__ = "0.1"

# Get the logger for this module
logger = logging.getLogger(__name__)

# Log that the package has been initialized
logger.info("Package initialized")
