import numpy as np
import tensorflow as tf


class KerasBlackBox:
    """
    统一的“黑箱”包装：
    - 接受 .h5 / SavedModel 路径
    - 暴露 predict_proba(X) 接口
    """

    def __init__(self, model_path: str, from_logits: bool = False):
        """
        model_path: artifacts/model/my_model.h5
        from_logits: 如果模型最后一层没 softmax，输出 logits，就设 True
        """
        self.model_path = model_path
        self.from_logits = from_logits

        # 真正加载 Keras 模型
        self.model = tf.keras.models.load_model(self.model_path)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        黑箱 predict_proba 接口：
        X: numpy array, shape = (batch, features)
        return: numpy array, shape = (batch, num_classes)
        """
        # 保一下是 np.ndarray
        if isinstance(X, tf.Tensor):
            X = X.numpy()

        y = self.model.predict(X)

        # 如果模型输出 logits，则手动 softmax
        if self.from_logits:
            y = tf.nn.softmax(y).numpy()

        return y
