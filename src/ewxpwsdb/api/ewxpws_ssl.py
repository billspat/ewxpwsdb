"""manages ssl configuration and errors messages if configuration for ssl is not correct. """
# Note: some posts etc show code to create an 'ssl_context' or import ssl, but when running the api 
#       with uvicorn, that library handles the creation of the ssl_context and we do not need to do that here

from dotenv import load_dotenv
from os import getenv, path
from typing import Tuple
import logging

# Set up logging
logger = logging.getLogger(__name__)

def get_ssl_files()->Tuple[str, str]:
    """looks for and returns the file names configured for SSL cert and key. 
    Attempting to run this method to use ssl will raises appropriate errors if files are not found. 
    
    Suggested usage:  
    try:
        cert_file, key_file = get_ssl_files()
        # use ssl in server
    except Exception as e:
        # issue warning
        # run server w/o ssl
        
    
    Has the side effect or loading the os env or reading .env file

    Raises:
        RuntimeError: if .env is not configured, or either file not is found.  Does not check for validity of files

    Returns:
        Tuple[str, str]: paths to the cert and key files
    """
    
    # TODO move this into a 'config.py' modules
    load_dotenv
    cert_file_path = getenv('EWXPWSDB_SSLCERT')
    key_file_path = getenv('EWXPWSDB_SSLKEY')
    

    if not cert_file_path or not key_file_path:
        raise RuntimeError("please set EWXPWSDB_SSLCERT and EWXPWSDB_SSLKEY to file paths in .env to use ssl")
    elif not path.exists(cert_file_path):
        raise RuntimeError(f"SSL cert file not found {cert_file_path}, can't load SSL")
    elif not path.exists(key_file_path):
        raise RuntimeError(f"SSL key file not found {cert_file_path}, can't load SSL")
    else:
        logger.info("SSL files found and loaded successfully")
        return (cert_file_path, key_file_path)
