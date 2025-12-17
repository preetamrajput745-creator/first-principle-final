import sys
import os
import json
from kafka import KafkaConsumer

# Add parent directory to path to import common
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import setup_logger
from common.storage import Storage

logger = setup_logger("ingest_worker")

def main():
    logger.info("Starting Ingestion Worker...")
    
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    storage = Storage()
    
    try:
        # Subscribe to all market.tick topics
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id="ingest_group",
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            # pattern='^market\.tick\..*' # Regex subscription
        )
        consumer.subscribe(pattern='^market\.tick\..*')
        
        logger.info("Connected to Kafka. Listening for ticks...")
        
        for message in consumer:
            topic = message.topic
            data = message.value
            symbol = topic.split('.')[-1] if len(topic.split('.')) > 2 else "UNKNOWN"
            
            logger.info(f"Received tick for {symbol}: {data}")
            
            # Persist to S3
            path = storage.upload_tick(symbol, data)
            if path:
                logger.info(f"Saved to S3: {path}")
            else:
                logger.error("Failed to save to S3")
                
    except Exception as e:
        logger.error(f"Error in ingestion worker: {e}")

if __name__ == "__main__":
    main()
