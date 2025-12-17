import json
import time
import boto3
from datetime import datetime, timedelta
import threading
from config import settings
from event_bus import event_bus
from database import SessionLocal, Signal, Order, Backtest

class ReplayEngine:
    """
    Replays raw ticks from S3 to simulate a past trading day.
    """
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY
        )
        self.is_running = False
        self.replay_speed = 1.0
        self.db = SessionLocal()

    def load_ticks(self, symbol, date_str):
        """Loads all tick files for a specific date from S3."""
        # Date str: YYYY-MM-DD
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        prefix = f"ticks/{symbol}/{dt.year}/{dt.month:02d}/{dt.day:02d}/"
        
        print(f"Loading ticks from {prefix}...")
        
        paginator = self.s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=settings.S3_BUCKET_TICKS, Prefix=prefix)
        
        ticks = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Get object
                    response = self.s3.get_object(Bucket=settings.S3_BUCKET_TICKS, Key=obj['Key'])
                    tick_data = json.loads(response['Body'].read().decode('utf-8'))
                    ticks.append(tick_data)
        
        # Sort by timestamp
        ticks.sort(key=lambda x: x['timestamp'])
        print(f"Loaded {len(ticks)} ticks.")
        return ticks

    def start_replay(self, symbol, date_str, speed=1.0):
        if self.is_running:
            print("Replay already running.")
            return
        
        print(f"Starting Replay for {symbol} on {date_str} at {speed}x speed.")
        self.is_running = True
        self.replay_speed = speed
        
        # Start in thread
        threading.Thread(target=self._replay_loop, args=(symbol, date_str)).start()

    def _replay_loop(self, symbol, date_str):
        ticks = self.load_ticks(symbol, date_str)
        if not ticks:
            print("No ticks found for replay.")
            self.is_running = False
            return

        print("Creating Backtest Record...")
        backtest = Backtest(
            automation_id="False Breakout",
            run_date=datetime.utcnow(),
            notes=f"Replay for {symbol} on {date_str}"
        )
        self.db.add(backtest)
        self.db.commit()

        # Publish Replay Start Event (Optional: To notify dashboard)
        event_bus.publish("system.replay.start", {"symbol": symbol, "date": date_str})

        start_time = time.time()
        first_tick_ts = datetime.fromisoformat(ticks[0]['timestamp'].replace("Z", "+00:00")).timestamp()
        
        for tick in ticks:
            if not self.is_running:
                break
                
            current_tick_ts = datetime.fromisoformat(tick['timestamp'].replace("Z", "+00:00")).timestamp()
            
            # Calculate how much real time should have passed
            time_elapsed_sim = current_tick_ts - first_tick_ts
            time_elapsed_real = (time.time() - start_time) * self.replay_speed
            
            # If simulation is ahead of real time (adjusted for speed), wait
            wait_time = (time_elapsed_sim / self.replay_speed) - (time.time() - start_time)
            if wait_time > 0:
                time.sleep(wait_time)
            
            # Publish Tick
            # Mark it as REPLAY so consumers can handle it (if logic differs, but ideally logic is same)
            # NOTE: We are pumping into SAME 'market.tick' topic. 
            # In production, we should restart workers with 'REPLAY_MODE' config or use separate topic.
            # For this MVP, we use the same topic but rely on the fact that LIVE ticks aren't coming at the same time presumably.
            # Best Practice: Workers should look at `settings.MODE` or msg flag.
            
            tick['is_replay'] = True
            event_bus.publish(f"market.tick.{symbol}", tick)
        
        self.is_running = False
        print("Replay Completed.")
        event_bus.publish("system.replay.end", {"symbol": symbol})

replay_engine = ReplayEngine()
