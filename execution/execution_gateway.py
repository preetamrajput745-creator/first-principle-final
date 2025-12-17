import json
import time
import os
import sys

# Add root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.execution.execution_service import ExecutionService

class ExecutionGateway:
    """
    ISOLATED SERVICE.
    This is the ONLY service that holds Broker Keys.
    It listens to confirmed signals and executes orders.
    """
    def __init__(self):
        # Delegate to the Secure Execution Service (Mistake #6 Compliance)
        self.execution_service = ExecutionService()
        if not self.execution_service.is_active:
            print("FATAL: Execution Service failed to initialize (Secrets missing?).")
            sys.exit(1)
            
        self.is_active = True
        print("SECURE: Execution Gateway Initialized with ExecutionService.")
    
    def execute_order(self, signal, is_approval_event=False):
        """
        Delegates execution to the secure ExecutionService.
        """
        if not isinstance(signal, dict):
            print(f"Invalid Signal: {signal}")
            return

        symbol = signal.get('symbol')
        price = signal.get('price', 0.0)
        action = signal.get('action', 'BUY') # Default to BUY if not specified
        quantity = signal.get('quantity', 1)
        
        # Prepare Order Request for Service
        order_request = {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "automation_id": signal.get("automation_id") # Needed for Gating
        }
        
        # Extract 2FA token if present (from Dashboard approval event)
        otp_token = signal.get('otp_token')
        
        # INTERNAL_AUTH_TOKEN required by Service
        # In a real microservice, this would be an mTLS cert or API Key
        INTERNAL_TOKEN = "INTERNAL_SECURE_TOKEN_XYZ"
        
        # Call Secure Service
        # If this is an approval event, we assume 'is_manual_approval=True'
        result = self.execution_service.execute_order(
            order_request, 
            auth_token=INTERNAL_TOKEN, 
            is_manual_approval=is_approval_event,
            otp_token=otp_token
        )
        
        status = result.get("status")
        
        if status == "FILLED":
            print(f"GATEWAY SUCCESS: {result}")
            # Publish Report
            event_bus.publish("exec.report", {
                "status": "FILLED",
                "symbol": symbol,
                "price": result.get("fill_price", price),
                "execution_id": result.get("execution_id"),
                "timestamp": time.time()
            })
            
        elif status == "REJECTED_GATING":
            print(f"GATEWAY BLOCKED: {result.get('reason')}")
            # Publish 'Approval Needed' event
            if not is_approval_event: # Don't loop if it failed *during* approval
                event_bus.publish("exec.approval_needed", {
                    "symbol": symbol,
                    "price": price,
                    "action": action,
                    "automation_id": signal.get("automation_id"), 
                    "reason": result.get("reason"),
                    "timestamp": time.time()
                })
        
        elif status == "REJECTED_2FA":
             print(f"GATEWAY SECURITY ALERT: 2FA Failed! {result.get('reason')}")
             # Could emit a security alert event here
             
        else:
            print(f"GATEWAY ERROR: {result}")

    def run(self):
        print("Execution Gateway Running (Isolated Layer)...")
        event_bus.subscribe("signal.confirmed", "exec_group", "gateway_1")
        event_bus.subscribe("exec.approve_command", "exec_group", "gateway_1") # Listen for approvals
        
        while self.is_active:
            # Poll both topics
            for topic in ["signal.confirmed", "exec.approve_command"]:
                messages = event_bus.read(topic, "exec_group", "gateway_1")
                for msg in messages:
                    msg_body = msg[1][0][1]
                    # Parse if string
                    if isinstance(msg_body, bytes): msg_body = msg_body.decode('utf-8')
                    if isinstance(msg_body, str): msg_body = json.loads(msg_body)
                    
                    msg_id = msg[1][0][0]
                    
                    if topic == "exec.approve_command":
                        print(f"USER APPROVAL RECEIVED for {msg_body.get('symbol')}")
                        self.execute_order(msg_body, is_approval_event=True)
                    else:
                        self.execute_order(msg_body, is_approval_event=False)
                        
                    event_bus.ack(topic, "exec_group", msg_id)
            time.sleep(0.1)

if __name__ == "__main__":
    gateway = ExecutionGateway()
    gateway.run()
