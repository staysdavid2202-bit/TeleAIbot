import matplotlib.pyplot as plt
import pandas as pd
import io

def generate_signal_chart(symbol, prices, direction):
    try:
        df = pd.DataFrame(prices, columns=["time", "close"])
        plt.figure(figsize=(4, 2))
        plt.plot(df["time"], df["close"], color="green" if direction == "long" else "red", linewidth=2)
        plt.title(f"{symbol} ({direction.upper()})", fontsize=10)
        plt.grid(alpha=0.3)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=120)
        plt.close()
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Ошибка при генерации графика для {symbol}: {e}")
        return None
