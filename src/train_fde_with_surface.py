# src/train_fde_with_surface.py

import os
import numpy as np
import tensorflow as tf

from engine.ml.background import save_background   # 你之前已经建的工具函数


# ================================
# 0) 准备一点“假数据”做 demo
#    （真实项目里你可以换成自己的数据）
# ================================
NUM_SAMPLES = 5000
NUM_FEATURES = 20

rng = np.random.RandomState(42)
X = rng.randn(NUM_SAMPLES, NUM_FEATURES).astype("float32")

# 造一个线性分隔的二分类标签
w_true = rng.randn(NUM_FEATURES, 1)
logits = X @ w_true
y = (logits > 0).astype("int32").ravel()

# 划分 train / test（这里只用 train）
X_train = X[:4000]
y_train = y[:4000]
X_test  = X[4000:]
y_test  = y[4000:]


# ================================
# 1) 建一个很简单的 Keras 模型
# ================================
from tensorflow import keras
from tensorflow.keras import layers

input_dim = X_train.shape[1]

model = keras.Sequential(
    [
        layers.Input(shape=(input_dim,)),
        layers.Dense(32, activation="relu"),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),  # 二分类
    ]
)

model.compile(
    optimizer="adam",
    loss="binary_crossentropy",
    metrics=["accuracy"],
)

print("\n=== START TRAINING ===")
model.fit(X_train, y_train, epochs=5, batch_size=32, verbose=1)

loss, acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Test accuracy: {acc:.4f}")

print("\n=== TRAINING COMPLETE ===")


# ================================
# 2) 确保 artifacts 目录存在
# ================================
os.makedirs("artifacts/model", exist_ok=True)
os.makedirs("artifacts/data", exist_ok=True)


# ================================
# 3) 保存模型为 .h5
# ================================
model_save_path = "artifacts/model/my_model.h5"
model.save(model_save_path)
print(f"[OK] Model saved to: {model_save_path}")


# ================================
# 4) 保存背景样本 background.npy
# ================================
X_train_np = np.array(X_train, dtype="float32")
background = X_train_np[:1000]
save_background(X_train_np, n_samples=1000)   # 里面会写到 artifacts/data/background.npy
print("[OK] Saved background.npy")


# ================================
# 5) 打印前 5 行 predict_proba 看看
# ================================
print("\n=== FINAL MODEL PREDICT (FIRST 5 SAMPLES) ===")
y_pred = model.predict(X_train_np[:5])
np.set_printoptions(precision=4, suppress=True)
print(y_pred)

print("\n[TRAIN SCRIPT COMPLETED SUCCESSFULLY]")
