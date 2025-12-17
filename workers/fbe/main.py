import sys
import os
import json
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer

# Add parent directory to path to import common
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import setup_logger
from common.database import SessionLocal
from common.models import Signal, Automation
from fbe.logic import FBEDetector

logger = setup_logger("fbe_worker")

def main():
    logger.info("Starting FBE Worker...")
    
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    db = SessionLocal()
    
    # Ensure default automation exists for linking
    # In a real app, this would be dynamic. For MVP, we get or create a default one.
    default_auto_id = None
    try:
        auto = db.query(Automation).filter_by(slug="fbe-default").first()
        if not auto:
            auto = Automation(name="False Breakout Default", slug="fbe-default", status="active", description="Default FBE Automation")
            db.add(auto)
            db.commit()
            logger.info("Created default automation entry")
        default_auto_id = auto.id
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        db.rollback()

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id="fbe_group",
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        consumer.subscribe(pattern='^market\.tick\..*')
        
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        detector = FBEDetector()
        
        logger.info("Connected to Kafka. Listening for ticks...")
        
        for message in consumer:
            topic = message.topic
            data = message.value
            symbol = topic.split('.')[-1] if len(topic.split('.')) > 2 else "UNKNOWN"
            
            price = data.get('price')
            timestamp_str = data.get('timestamp') # Assuming ISO string
            
            if price:
                signal_payload = detector.process_tick(symbol, price, timestamp_str)
                
                if signal_payload:
                    logger.info(f"FBE DETECTED: {signal_payload}")
                    
                    # 1. Publish to Kafka
                    producer.send("signal.false_breakout", signal_payload)
                    
                    # 2. Persist to DB
                    try:
                        # Convert timestamp string to datetime if needed, or use current time if missing
                        ts = datetime.now() 
                        if timestamp_str:
                            try:
                                ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            except:
                                pass

                        signal_entry = Signal(
                            automation_id=default_auto_id,
                            symbol=symbol,
                            timestamp=ts,
                            score=1.0, # FBE is binary in this logic
                            payload=signal_payload,
                            status="new"
                        )
                        db.add(signal_entry)
                        db.commit()
                        logger.info("Signal saved to DB")
                    except Exception as db_err:
                        logger.error(f"Failed to save signal to DB: {db_err}")
                        db.rollback()
                    
    except Exception as e:
        logger.error(f"Error in FBE worker: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
