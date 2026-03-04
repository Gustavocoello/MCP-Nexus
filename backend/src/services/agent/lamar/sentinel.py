# src/services/llm/lamar/sentinel.py
import os
import gc
import time
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from src.config.time_helper import get_now, TIMEZONE
from langchain_core.messages import HumanMessage
from src.database.models.models import PingLog
from src.database.config.connection import SessionLocal
from .alerts import send_429_email
from .memory import is_provider_blocked, set_provider_cooldown

class LamarSentinel:
    def __init__(self, providers_list):
        self.providers = providers_list
        print(f"Lamar --> loaded with {len(self.providers)} providers.")

    def test_all_providers(self, force=False):
        now = get_now()
        hace_una_hora = now - timedelta(minutes=60)
        print(f"[Lamar Sentinel] Starting real test for {len(self.providers)} providers")
        results = []

        if not self.providers:
            print("ERROR: Provider list is empty.")
            return results

        session = SessionLocal()
        try:
            for i, p in enumerate(self.providers):
                print(f"Number: {i} Processing: {p.get('name', 'No Name')}")
                try:
                    last_success = session.query(PingLog).filter(
                        PingLog.service == p['name'],
                        PingLog.status_code == 200,
                    ).order_by(PingLog.timestamp.desc()).first()  # sin filtro de fecha

                    if last_success:
                        db_ts = last_success.timestamp
                        # Normalize timezone before comparing
                        if db_ts.tzinfo is None:
                            db_ts = TIMEZONE.localize(db_ts)
                        else:
                            db_ts = db_ts.astimezone(TIMEZONE)

                        if db_ts >= hace_una_hora:
                            print(f"[CACHE] {p['name']} OK. Skipping...")
                            results.append({
                                "name": p['name'],
                                "status": {"alive": True, "details": "Recently verified"}
                            })
                            continue
                except Exception as e:
                    print(f"Warning: Date error for {p['name']}: {e}. Proceeding to real test.")

                if is_provider_blocked(p['name']):
                    print(f"[SKIP] {p['name']} is in cooldown.")
                    continue

                status = self.check_capabilities(p)
                self.save_status_to_db(p['name'], status)

                if status['error_code'] == 429:
                    send_429_email(p['name'], status['details'])
                    set_provider_cooldown(p['name'], minutes=30)
                elif not status['alive']:
                    set_provider_cooldown(p['name'], minutes=5)

                results.append({"name": p['name'], "status": status})
                gc.collect()
                time.sleep(0.3)
        finally:
            session.close()

        return results

    def check_capabilities(self, config):
        try:
            llm = ChatOpenAI(
                base_url=config['base_url'],
                api_key=os.getenv(config['key']),
                model=config['model'],
                max_retries=0,
                timeout=20
            )
            start_time = time.time()
            llm.invoke([HumanMessage(content="Reply only 'OK'")])
            latency = (time.time() - start_time) * 1000

            return {
                "alive": True,
                "latency_ms": latency,
                "supports_tools": True,
                "error_code": 200,
                "details": "Working correctly"
            }
        except Exception as e:
            error_str = str(e)
            code = 429 if "429" in error_str else 500
            return {
                "alive": False,
                "latency_ms": 0,
                "supports_tools": False,
                "error_code": code,
                "details": error_str
            }

    def save_status_to_db(self, name, status_data):
        session = SessionLocal()
        try:
            new_ping = PingLog(
                service=name,
                event_type="LAMAR_SENTINEL_CHECK",
                message=status_data['details'],
                response_ms=int(status_data['latency_ms']),
                status_code=int(status_data['error_code']),
                timestamp=get_now()
            )
            session.add(new_ping)
            session.commit()
        except Exception as e:
            print(f"DB Error Sentinel ({name}): {e}")
            session.rollback()
        finally:
            session.close()