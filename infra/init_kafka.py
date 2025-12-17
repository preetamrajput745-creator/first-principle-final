from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import os
import time

def create_topics():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Wait for Kafka to be ready
    print("Waiting for Kafka...")
    time.sleep(10) 
    
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers, 
            client_id='admin_client'
        )
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}")
        return

    topics = [
        NewTopic(name="market.tick", num_partitions=1, replication_factor=1), # Wildcards not supported in creation, using generic topic or specific? User said market.tick.<symbol>
        # Kafka supports auto-creation, but good to have base topics if we use a single topic with keys, or we can just let them auto-create.
        # However, user specified "market.tick.<symbol>". Creating all possible symbols is impossible.
        # We will create the fixed topics.
        NewTopic(name="signal.false_breakout", num_partitions=1, replication_factor=1),
        NewTopic(name="exec.order.request", num_partitions=1, replication_factor=1),
        NewTopic(name="exec.order.status", num_partitions=1, replication_factor=1),
        NewTopic(name="audit.events", num_partitions=1, replication_factor=1),
    ]

    # For dynamic topics like market.tick.<symbol>, we usually rely on auto.create.topics.enable=true 
    # or create them on the fly. 
    # For this script, we'll just create the static ones.

    try:
        admin_client.create_topics(new_topics=topics, validate_only=False)
        print("Topics created successfully.")
    except TopicAlreadyExistsError:
        print("Topics already exist.")
    except Exception as e:
        print(f"Error creating topics: {e}")
    finally:
        admin_client.close()

if __name__ == "__main__":
    create_topics()
