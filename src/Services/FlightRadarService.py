import asyncio
import logging

logger = logging.getLogger(__name__)

async def fr_test():
    """Test stub for FlightRadar extraction"""
    logger.info("[FR_TEST] Background task started")
    
    for i in range(1, 6):
        logger.info(f"[FR_TEST] Step {i}/5")
        await asyncio.sleep(2)
    
    logger.info("[FR_TEST] Background task completed")
