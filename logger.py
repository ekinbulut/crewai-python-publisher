# project/logger.py
import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("crew_blog.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("crew_blog")
