
"""
train_fde_with_surface.py

Toy FDE-style training loop + loss surface visualization.

你可以把它当成模板：
- 把 TinyFDEClassifier 换成你的 FDE classifier / policy / C 模型
- 把 get_batch() 换成你的 DataLoader
- 把 lambda_clean / lambda_adv / pgd_attack 替换到你现有 pipeline

依赖：
    pip install torch matplotlib numpy
"""

import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from loss_surface_adapter import LossSurfaceExplorer  # 确保这个文件在 PYTHONPATH 或同目录

device = "cuda" if torch.cuda.is_available() else "cpu"


# -----------------------------
# 1. 一个占位 FDE classifier
# -----------------------------
class TinyFDEClassifier(nn.Module):
    """
    占位网络结构：
    - Conv -> ReLU -> Conv -> ReLU -> GAP -> FC
    你可以把它直接替换为你现在 FDE 用的 classifier / policy net。
    """

    def __init__(self, in_ch=1, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_ch, 32, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Linear(64, num_classes)

    def forward(self, x):
        h = self.features(x)            # (B, 64, 1, 1)
        h = h.view(x.size(0), -1)       # (B, 64)
        logits = self.fc(h)             # (B, num_classes)
        return logits


# -----------------------------
# 2. PGD 对抗攻击
# -----------------------------
def pgd_attack(model, x, y, eps=0.3, alpha=0.01, iters=40):
    """
    简单 PGD-L∞ 版本，用于在输入空间生成 x_adv。

    - x:    clean input, shape (B, C, H, W)
    - y:    labels
    - eps:  L∞ 约束半径
    - alpha:每步更新步长
    - iters:迭代次数
    """
    model.eval()
    x_adv = x.detach().clone()
    x_adv.requires_grad = True

    for _ in range(iters):
        logits = model(x_adv)
        loss = F.cross_entropy(logits, y)
        loss.backward()

        # FGSM step
        with torch.no_grad():
            grad_sign = x_adv.grad.sign()
            x_adv = x_adv + alpha * grad_sign

            # projection to eps-ball around x
            eta = torch.clamp(x_adv - x, min=-eps, max=eps)
            x_adv = torch.clamp(x + eta, 0.0, 1.0)

        x_adv.requires_grad = True
        model.zero_grad()

    return x_adv.detach()


# -----------------------------
#
# -----------------------------
def get_fake_batch(batch_size=32, img_size=32, num_classes=10):
    x = torch.rand(batch_size, 1, img_size, img_size, device=device)
    y = torch.randint(0, num_classes, (batch_size,), device=device)
    return x, y


# -----------------------------
# 4. 定义 clean+adv loss
# -----------------------------
def make_loss_fn(lambda_clean=1.0, lambda_adv=1.0, eps=0.3, alpha=0.01, iters=10):
    """
    返回一个 loss_fn(model, batch) -> scalar 的函数，
    供 LossSurfaceExplorer 使用。
    """

    def loss_fn(model: nn.Module, batch):
        x, y = batch
        x = x.to(device)
        y = y.to(device)

        # clean
        logits_clean = model(x)
        L_clean = F.cross_entropy(logits_clean, y)

        # adv (在 model 当前参数下生成 PGD 对抗样本)
        x_adv = pgd_attack(model, x, y, eps=eps, alpha=alpha, iters=iters)
        logits_adv = model(x_adv)
        L_adv = F.cross_entropy(logits_adv, y)

        # 总 loss（FDE 风格：clean + adv）
        L_total = lambda_clean * L_clean + lambda_adv * L_adv
        return L_total

    return loss_fn


# -----------------------------
#
# -----------------------------
def train_with_surface(num_epochs=5, lambda_clean=1.0, lambda_adv=1.0):
    model = TinyFDEClassifier().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    # 生成用于 surface 的 loss 函数
    surface_loss_fn = make_loss_fn(
        lambda_clean=lambda_clean,
        lambda_adv=lambda_adv,
        eps=0.3,
        alpha=0.01,
        iters=5,
    )

    explorer = LossSurfaceExplorer(model, surface_loss_fn, device=device)

    for epoch in range(1, num_epochs + 1):
        model.train()
        x, y = get_fake_batch(batch_size=64)
        logits = model(x)
        loss = F.cross_entropy(logits, y)
        opt.zero_grad()
        loss.backward()
        opt.step()

        print(f"[Epoch {epoch}] train CE loss = {loss.item():.4f}")

        # 每隔若干个 epoch 做一次 loss surface 可视化
        if epoch in [1, num_epochs]:
            # 用同一 batch 观测参数空间附近的 loss surface
            x_vis, y_vis = get_fake_batch(batch_size=32)
            batch_vis = (x_vis, y_vis)
            title = f"Loss surface at epoch {epoch} (lambda_clean={lambda_clean}, lambda_adv={lambda_adv})"
            explorer.plot_2d_surface(batch_vis, radius=0.5, grid_size=21, title=title)


if __name__ == "__main__":
    # 示例 1：lambda_clean = 1, lambda_adv = 1
    print("=== Example: lambda_clean=1.0, lambda_adv=1.0 ===")
    train_with_surface(num_epochs=3, lambda_clean=1.0, lambda_adv=1.0)

    # 你可以复制多跑几次，用不同的 lambda 观察 surface 变化：
    # print("=== Example: lambda_clean=5.0, lambda_adv=1.0 ===")
    # train_with_surface(num_epochs=3, lambda_clean=5.0, lambda_adv=1.0)
