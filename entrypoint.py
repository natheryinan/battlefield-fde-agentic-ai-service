import os
import time
import logging

from fde_bootstrap import build_engine

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("tiny-supervisor")


def _run_engine(engine):
    # 兼容不同入口名
    for fn in ("run_forever", "serve", "loop", "run", "start"):
        if hasattr(engine, fn):
            return getattr(engine, fn)()

    # TinyEngine 没有入口：就让进程常驻（decoy heartbeat）
    log.warning("TinyEngine 无 run/serve/loop/run_forever；进入 heartbeat 常驻")
    while True:
        time.sleep(30)
        log.info("tiny alive (heartbeat)")


def run_forever():
    os.environ["FDE_PUBLIC_MODE"] = "1"  # 强制 tiny decoy

    backoff = 1.0
    while True:
        try:
            engine, mode, personas, router = build_engine(None)
            log.info(f"boot ok mode={mode} personas={list(personas.keys())}")

            backoff = 1.0  # 成功启动就重置
            _run_engine(engine)

            log.warning("engine stopped normally; restarting...")
        except KeyboardInterrupt:
            log.info("stop by ctrl+c")
            break
        except AttributeError as e:
            log.error(f"FATAL: {e}")
            break
        except Exception:
            log.exception("engine crashed; restarting...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)


if __name__ == "__main__":
    run_forever()
