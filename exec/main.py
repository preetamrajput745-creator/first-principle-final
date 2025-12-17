
import sys
import os
import json
import time
import random
import uuid
from datetime import datetime

# Add parent directory to path to import common
# Add parent directory to path to import common
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)
sys.path.append(os.path.join(root_path, "workers"))

from event_bus import event_bus
from workers.execution.execution_service import ExecutionService
from common.database import get_db
from common.models import Order, Signal

def main():
    print("Starting Execution Service (Redis Worker)...")
    
    # Initialize Execution Service (Handles Vault, Gating, Safety)
    exec_service = ExecutionService()
    
    # Subscribe to signals
    # Subscribe to signals AND approvals
    topic_signal = "signal.new"
    topic_approval = "exec.approve_command"
    group = "exec_group"
    consumer = "exec_worker_1"
    
    event_bus.subscribe(topic_signal, group, consumer)
    event_bus.subscribe(topic_approval, group, consumer)
    
    print(f"Subscribed to {topic_signal} and {topic_approval}. Waiting for events...")
    
    while True:
        try:
            # Poll both topics
            for topic in [topic_signal, topic_approval]:
                messages = event_bus.read(topic, group, consumer)
                
                for msg_id, msg_data in messages:
                    # Clean data if it's double serialized
                    if isinstance(msg_data, str):
                        try:
                            msg_data = json.loads(msg_data)
                        except: pass
                    
                    is_approval = (topic == topic_approval)
                    print(f"Processing {'APPROVAL' if is_approval else 'SIGNAL'}: {msg_data}")
                    
                    # 1. Prepare Order Request
                    order_req = {
                        "automation_id": msg_data.get("automation_id"), 
                        "symbol": msg_data.get("symbol"),
                        "action": msg_data.get("action", "BUY"),
                        "quantity": int(msg_data.get("quantity", 1)),
                        "price": float(msg_data.get("price", 0.0)) # Market if 0
                    }
                    
                    # 2. Call Secure Execution Service
                    auth_token = "INTERNAL_SECURE_TOKEN_XYZ"
                    otp_token = msg_data.get("otp_token")
                    
                    result = exec_service.execute_order(
                        order_req, 
                        auth_token, 
                        is_manual_approval=is_approval,
                        otp_token=otp_token
                    )
                    
                    if result["status"] == "FILLED":
                        # 3. Simulate Execution
                        limit_price = order_req["price"] if order_req["price"] > 0 else 100.0 # Fallback
                        drift_pct = random.uniform(-0.0001, 0.0003) 
                        fill_price = limit_price * (1 + drift_pct)
                        realized_slippage = abs(fill_price - limit_price)
                        
                        pnl_pct = random.uniform(-0.01, 0.015)
                        pnl_amount = (fill_price * order_req["quantity"]) * pnl_pct
                        
                        # Save
                        with next(get_db()) as db:
                             order = Order(
                                signal_id=uuid.UUID(msg_data["signal_id"]) if "signal_id" in msg_data else None,
                                symbol=order_req["symbol"],
                                side=order_req["action"],
                                quantity=order_req["quantity"],
                                price=limit_price,
                                status="FILLED",
                                realized_slippage=realized_slippage,
                                simulated_slippage=0.0,
                                pnl=pnl_amount,
                                is_paper=True,
                                exit_price=fill_price + (fill_price * pnl_pct),
                                exit_time=datetime.utcnow()
                             )
                             db.add(order)
                             db.commit()
                             print(f"ORDER FILLED: PnL=${pnl_amount:.2f}")
                        
                        event_bus.publish("order.filled", {
                            "symbol": order_req["symbol"],
                            "pnl": pnl_amount,
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    elif result["status"] == "REJECTED_GATING":
                        print(f"ORDER BLOCKED (Gating): {result['reason']}")
                        # Don't save Gating rejections as failed orders to keep DB clean, 
                        # or save as 'PENDING' if we implemented that state.
                        # For now, just log.

                    else:
                        print(f"ORDER REJECTED: {result['reason']}")
                        # Save Rejection
                        with next(get_db()) as db:
                             order = Order(
                                signal_id=uuid.UUID(msg_data["signal_id"]) if "signal_id" in msg_data else None,
                                symbol=order_req["symbol"],
                                side=order_req["action"],
                                quantity=order_req["quantity"],
                                price=order_req["price"],
                                status="REJECTED",
                                pnl=0.0
                             )
                             db.add(order)
                             db.commit()

                    event_bus.ack(topic, group, msg_id)
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"ERROR in Execution Worker: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)

if __name__ == "__main__":
    main()
