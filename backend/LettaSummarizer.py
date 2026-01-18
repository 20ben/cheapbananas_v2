from dotenv import load_dotenv
import os
from letta_client import Letta
from AsyncLettaMinion import AsyncLettaMinion
from AsyncLettaReader import AsyncLettaReader
import asyncio
import threading
import time
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LettaManagerV2:
    """
    Manages multiple Letta minions using manual threading (no thread pool)
    """
    
    def __init__(self):
        """Initialize the LettaManager and load environment variables"""
        # Load environment variables
        load_dotenv()
        
        # Get API token
        self.api_token = os.environ.get('LETTA_API_TOKEN')
        if self.api_token is None:
            raise ValueError("LETTA_API_TOKEN environment variable not set")
        
        self.reader_id = os.environ.get('READER_ID')
        if self.reader_id is None:
            raise ValueError("READER_ID environment variable not set")
    
    async def _run_minion_async(self, minion_id, data):
        """
        Async function to run a single minion
        
        Args:
            minion_id: ID of the Letta minion
            data: Data to pass to save_deals (name, location, etc.)
        """
        logger.info(f"Starting minion {minion_id} with data: {data}")
        try:
            minion = AsyncLettaMinion(self.api_token, minion_id)
            await minion.connect_agent()
            print("DATA<>,", data)
            result = await minion.save_deals(*(data))
            logger.info(f"Minion {minion_id} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Minion {minion_id} failed: {str(e)}", exc_info=True)
            raise
    
    def _run_minion_thread(self, minion_id, data, results, index):
        """
        Thread wrapper that runs the async minion function
        
        Args:
            minion_id: ID of the Letta minion
            data: Data to process
            results: Shared dict to store results
            index: Index in results dict
        """
        try:
            result = asyncio.run(self._run_minion_async(minion_id, data))
            results[index] = {
                "success": True,
                "minion_id": minion_id,
                "result": result,
                "data": data
            }
        except Exception as e:
            results[index] = {
                "success": False,
                "minion_id": minion_id,
                "error": str(e),
                "data": data
            }
    
    async def process_restaurants(self, restaurant_data):
        """
        Process restaurant data using multiple minions with manual threading
        
        Args:
            restaurant_data: List of restaurant data, each item should be [name, location]
                            Example: [["TP Tea", "Berkeley"], ["Sharetea", "Berkeley"]]
        
        Returns:
            dict with results from all minions
        """
        logger.info(f"Starting to process {len(restaurant_data)} restaurants")
        
        # Limit to available minions
        num_to_process = min(len(restaurant_data), len(self.minion_ids))
        restaurants_to_process = restaurant_data[:num_to_process]
        
        # Results storage (shared across threads)
        results = {}
        
        # Create and start threads manually
        threads = []
        for index, (minion_id, data) in enumerate(zip(self.minion_ids, restaurants_to_process)):
            t = threading.Thread(
                target=self._run_minion_thread,
                args=(minion_id, data, results, index)
            )
            threads.append(t)
            t.start()
            logger.info(f"Started thread {index} for minion {minion_id}")
        
        # Wait for all threads to complete
        for index, t in enumerate(threads):
            t.join()
            logger.info(f"Thread {index} completed")
        
        # Calculate statistics
        successful = sum(1 for r in results.values() if r["success"])
        failed = len(results) - successful
        
        logger.info(f"Processing complete: {successful}/{len(results)} succeeded")
        
        reader = AsyncLettaReader(self.api_token, self.reader_id)

        data = {}
        for r in restaurant_data:
            deals_info = await reader.read_deals(r[0], r[1])
            if deals_info:  # ignore empty dicts
                name = deals_info['name']
                deals = deals_info['deals']
                data[name] = deals  # store deals by restaurant name

        return data
