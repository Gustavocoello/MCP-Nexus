# src/services/agent/lamar/tools/sentinel.py
import os
import gc
import time
from datetime import timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.core.time_helper import get_now, TIMEZONE
from src.database.models.models import PingLog
from src.database.settings.connection import get_db

# ---- HELPERS --- 
def set_provider_cooldown(provider_name, minutes=60):
    """Marca un proveedor como 'No Disponible' por N minutos."""
    try:
        db = next(get_db())
        unlock_time = get_now() + timedelta(minutes=minutes)
        message = f"cooldown|until:{unlock_time.strftime('%H:%M')}"
        
        stat = PingLog(
            service=provider_name[:18],
            event_type="provider_cooldown",
            message=message,
            status_code=429,
            response_ms=0,
            client_ip="lamar",
            next_ping_sc=minutes * 60,
            timestamp=get_now()
        )
        db.add(stat)
        db.commit()
    except Exception as e:
        if 'db' in locals(): db.rollback()
        print(f"Error setting cooldown for {provider_name}: {str(e)}")
    finally:
        if 'db' in locals(): db.close()

def is_provider_blocked(provider_name):
    """Verifica si el proveedor sigue en su periodo de cooldown."""
    try:
        db = next(get_db())
        last_status = db.query(PingLog)\
            .filter(PingLog.service == provider_name)\
            .filter(PingLog.event_type == "provider_cooldown")\
            .order_by(PingLog.timestamp.desc()).first()

        if last_status and last_status.next_ping_sc:
            unlock_time = last_status.timestamp + timedelta(seconds=last_status.next_ping_sc)
            
            if unlock_time.tzinfo is None:
                unlock_time = TIMEZONE.localize(unlock_time)
            else:
                unlock_time = unlock_time.astimezone(TIMEZONE)
                
            return get_now() < unlock_time

        return False
    except Exception as e:
        print(f"Error checking cooldown for {provider_name}: {str(e)}")
        return False
    finally:
        if 'db' in locals(): db.close()
        
        
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

        try:
            db = next(get_db())
            for i, p in enumerate(self.providers):
                print(f"Number: {i} Processing: {p.get('name', 'No Name')}")
                try:
                    last_success = db.query(PingLog).filter(
                        PingLog.service == p['name'],
                        PingLog.status_code == 200,
                    ).order_by(PingLog.timestamp.desc()).first()

                    if last_success:
                        db_ts = last_success.timestamp
                        if db_ts.tzinfo is None:
                            db_ts = TIMEZONE.localize(db_ts)
                        else:
                            db_ts = db_ts.astimezone(TIMEZONE)

                        if db_ts >= hace_una_hora and not force:
                            print(f"[CACHE] {p['name']} OK. Skipping...")
                            results.append({
                                "name": p['name'],
                                "status": {"alive": True, "details": "Recently verified"}
                            })
                            continue
                except Exception as e:
                    print(f"Warning: Date error for {p['name']}: {str(e)}. Proceeding to real test.")

                if is_provider_blocked(p['name']):
                    print(f"[SKIP] {p['name']} is in cooldown.")
                    continue

                status = self.check_capabilities(p)
                self.save_status_to_db(p['name'], status)

                if status['error_code'] == 429:
                    # send_429_email(p['name'], status['details']) # Opcional: descomentar si tienes configurado alerts.py
                    set_provider_cooldown(p['name'], minutes=30)
                elif not status['alive']:
                    set_provider_cooldown(p['name'], minutes=5)

                results.append({"name": p['name'], "status": status})
                gc.collect()
                time.sleep(0.3)
                
        except StopIteration:
            print("ERROR: Could not get DB session in Sentinel.")
        finally:
            if 'db' in locals(): db.close()

        return results

    def check_capabilities(self, config):
        try:
            base_url = config['base_url']
            
            if not base_url.startswith("http"):
                account_id = os.getenv(base_url)
                if not account_id:
                    return {
                        "alive": False, "latency_ms": 0,
                        "supports_tools": False, "error_code": 500,
                        "details": f"env var {base_url} not set"
                    }
                base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

            if "key_func" in config:
                api_key_value = config['key_func']()
            else:
                api_key_value = os.getenv(config.get('key'))
                if not api_key_value:
                    api_key_value = config.get('key')
            
            llm = ChatOpenAI(
                base_url=base_url,
                api_key=api_key_value,
                model=config['model'],
                max_retries=0,
                timeout=20
            )
            start_time = time.time()
            llm.invoke([HumanMessage(content="Reply only 'OK'")])
            latency = (time.time() - start_time) * 1000

            return {
                "alive": True, "latency_ms": latency,
                "supports_tools": True, "error_code": 200,
                "details": "Working correctly"
            }
        except Exception as e:
            error_str = str(e)
            code = 429 if "429" in error_str else 500
            return {
                "alive": False, "latency_ms": 0,
                "supports_tools": False, "error_code": code,
                "details": error_str
            }

    def save_status_to_db(self, name, status_data):
        code = int(status_data['error_code'])
        latency = int(status_data['latency_ms'])
        details_short = status_data['details'][:48]
        message = f"{code}|{details_short}"
        
        try:
            db = next(get_db())
            new_ping = PingLog(
                service=name[:20],
                event_type="lamar_sentinel_check",
                message=message,
                response_ms=latency,
                status_code=code,
                client_ip="lamar_sentinel",
                timestamp=get_now()
            )
            db.add(new_ping)
            db.commit()
        except Exception as e:
            if 'db' in locals(): db.rollback()
            print(f"DB Error Sentinel ({name}): {str(e)}")
        finally:
            if 'db' in locals(): db.close()