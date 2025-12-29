import torch
import torch.nn as nn
import torch.nn.functional as F


class FDEClassifier(nn.Module):
    """
    FDE-style classifier / C 模型占位版：
    - 输入:  (B, in_ch, H, W)，例如 (B, 1, 32, 32) 或 (B, 1, 256, 256)
    - 输出:  (B, num_classes) 的 logits，用于 CE / PGD 等

    结构:
      Conv(1 -> 32) -> ReLU
      Conv(32 -> 64) -> ReLU
      Conv(64 -> 128) -> ReLU
      GlobalAvgPool -> FC(128 -> num_classes)
    """

    def __init__(self, in_ch: int = 1, num_classes: int = 10):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(in_ch, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),

            # 无论输入多大，这里都池化到 1x1，方便接 FC
            nn.AdaptiveAvgPool2d(1),
        )

        self.fc = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, C, H, W)
        return: logits (B, num_classes)
        """
        h = self.features(x)          # (B, 128, 1, 1)
        h = h.view(x.size(0), -1)     # (B, 128)
        logits = self.fc(h)           # (B, num_classes)
        return logits
