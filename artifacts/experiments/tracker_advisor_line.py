
# artifacts/experiments/track_advisor_line.py

from engine.regime_router import RegimeRouter

def demo():
    router = RegimeRouter()

    bands = ["CALM","TENSE","TENSE","HOSTILE","CALM"]

    print("band     | advisor     | event")
    print("--------------------------------")

    for band in bands:
        ev = router.step(band)
        name = ev.advisor.value if ev.advisor else "主独行"
        print(f"{band:<8} | {name:<10} | {ev.event}")

if __name__ == "__main__":
    demo()
