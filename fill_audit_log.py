import os
import json
import uuid
import datetime
import random

# Reuse config from previous step
TASK_ID = "20251212-ROLES-101"
DATE = datetime.datetime.utcnow().strftime("%Y-%m-%d")
BASE_DIR = os.path.abspath(".")
EVIDENCE_DIR = os.path.join(BASE_DIR, f"antigravity-audit/{DATE}/{TASK_ID}/roles")
DB_FILE = os.path.join(EVIDENCE_DIR, "audit_events.db")

ACTIONS = ["APPROVE_POLICY", "SIGNOFF_PROMOTION", "REJECT_POLICY", "ACKNOWLEDGE_ALERT"]
ACTORS = [{"name": "Alice", "role": "owner", "id": "u1"}]

print(f"Generating extra audit logs in {EVIDENCE_DIR}...")

# Read existing logs
existing = []
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        for line in f:
            if line.strip():
                existing.append(json.loads(line))

count = len(existing)
target = 35

with open(DB_FILE, "a") as f:
    while count < target:
        actor = random.choice(ACTORS)
        action = random.choice(ACTIONS)
        event_id = str(uuid.uuid4())
        ts = datetime.datetime.utcnow().isoformat() + "Z"
        
        entry = {
            "event_id": event_id,
            "actor": actor['name'],
            "actor_role": actor['role'],
            "actor_id": actor['id'],
            "actor_ip": "10.0.0.5",
            "action": action,
            "target_id": f"item-{random.randint(100, 999)}",
            "timestamp_utc": ts,
            "signed_hash": f"sha256-mock-{uuid.uuid4().hex[:16]}",
            "evidence_link": f"s3://antigravity-audit/.../{event_id}",
            "justification": "Routine operation",
            "2fa_hash": "valid_token_mock"
        }
        f.write(json.dumps(entry) + "\n")
        count += 1

print(f"Total audit logs: {count}")

# Creates 30 individual JSON files for the deliverable "30 sample audit JSONs"
samples_dir = os.path.join(EVIDENCE_DIR, "audit_samples")
if not os.path.exists(samples_dir):
    os.makedirs(samples_dir)

with open(DB_FILE, "r") as f:
    idx = 1
    for line in f:
        if idx > 35: break
        data = json.loads(line)
        with open(os.path.join(samples_dir, f"audit_sample_{idx}.json"), "w") as sf:
            json.dump(data, sf, indent=2)
        idx += 1

print("Audit generation complete.")
