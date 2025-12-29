import numpy as np
import tensorflow as tf

class KerasBlackBox:
    def __init__(self, model_path: str, from_logits: bool = False):
        # 自动加载 SavedModel / .h5
        self.model = tf.keras.models.load_model(model_path)
        self.from_logits = from_logits

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        黑箱 predict_proba 接口
        X: numpy array, shape = (batch, features)
        return: numpy array, shape = (batch, num_classes)
        """
        y = self.model.predict(X)

        # 如果模型输出 logits → 转 softmax
        if self.from_logits:
            y = tf.nn.softmax(y).numpy()

        return y
