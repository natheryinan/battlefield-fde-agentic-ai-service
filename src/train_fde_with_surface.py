
"""
train_fde_with_surface.py

FDE-style classifier training + loss surface visualization.

你需要：
    - src/models/fde_classifier.py
    - src/utils/loss_surface_adapter.py

运行方式：
    cd src
    python train_fde_with_surface.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from utils.loss_surface_adapter import LossSurfaceExplorer
from models import FDEClassifier   # ← 你在 models/__init__.py 已经导出


device = "cuda" if torch.cuda.is_available() else "cpu"


# -----------------------------------------------------
# 1. PGD Attack（用于生成 adversarial examples）
# -----------------------------------------------------
def pgd_attack(model, x, y, eps=0.3, alpha=0.01, iters=40):
    """
    PGD (L∞) 对抗攻击，在输入空间制造 x_adv。
    """
    model.eval()
    x_adv = x.clone().detach().to(device)
    x_adv.requires_grad = True

    for _ in range(iters):
        logits = model(x_adv)
        loss = F.cross_entropy(logits, y)
        loss.backward()

        with torch.no_grad():
            grad_sign = x_adv.grad.sign()
            x_adv = x_adv + alpha * grad_sign

            # 投影到 L∞-ball
            eta = torch.clamp(x_adv - x, min=-eps, max=eps)
            x_adv = torch.clamp(x + eta, 0.0, 1.0)

        x_adv = x_adv.detach()
        x_adv.requires_grad = True
        model.zero_grad()

    return x_adv.detach()


# -----------------------------------------------------
# 2. 假 batch（你可以改成真实 dataloader）
# -----------------------------------------------------
def get_fake_batch(batch_size=32, img_size=32, num_classes=10):
    x = torch.rand(batch_size, 1, img_size, img_size, device=device)
    y = torch.randint(0, num_classes, (batch_size,), device=device)
    return x, y


# -----------------------------------------------------
# 3. 定义 FDE-style clean+adv loss（供 surface explorer 使用）
# -----------------------------------------------------
def make_loss_fn(lambda_clean=1.0, lambda_adv=1.0, eps=0.3, alpha=0.01, iters=10):
    """
    返回一个可调用 loss_fn(model, batch) 的 closure。
    """

    def loss_fn(model: nn.Module, batch):
        x, y = batch
        x = x.to(device)
        y = y.to(device)

        # ----- clean -----
        logits_clean = model(x)
        L_clean = F.cross_entropy(logits_clean, y)

        # ----- adv -----
        x_adv = pgd_attack(model, x, y, eps=eps, alpha=alpha, iters=iters)
        logits_adv = model(x_adv)
        L_adv = F.cross_entropy(logits_adv, y)

        # ----- 总 loss -----
        L_total = lambda_clean * L_clean + lambda_adv * L_adv
        return L_total

    return loss_fn


# -----------------------------------------------------
# 4. 训练 + 可视化
# -----------------------------------------------------
def train_with_surface(num_epochs=3, lambda_clean=1.0, lambda_adv=1.0):
    """
    训练 FDEClassifier，并在 epoch 1 & epoch N 可视化 loss surface。
    """
    model = FDEClassifier(in_ch=1, num_classes=10).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # surface loss 准备好
    surface_loss_fn = make_loss_fn(
        lambda_clean=lambda_clean,
        lambda_adv=lambda_adv,
        eps=0.3,
        alpha=0.01,
        iters=5,
    )

    explorer = LossSurfaceExplorer(model, surface_loss_fn, device=device)

    print("Training FDEClassifier...\n")

    for epoch in range(1, num_epochs + 1):
        model.train()

        # ------- 训练 step -------
        x, y = get_fake_batch(batch_size=64, img_size=32, num_classes=10)
        logits = model(x)
        loss = F.cross_entropy(logits, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        print(f"[Epoch {epoch}] CE loss = {loss.item():.4f}")

        # ------- 可视化 -------
        if epoch in [1, num_epochs]:
            x_vis, y_vis = get_fake_batch(batch_size=32, img_size=32)
            batch_vis = (x_vis, y_vis)

            title = (
                f"Loss surface at epoch {epoch} "
                f"(lambda_clean={lambda_clean}, lambda_adv={lambda_adv})"
            )

            explorer.plot_2d_surface(
                batch_vis,
                radius=0.5,
                grid_size=21,
                title=title,
            )


if __name__ == "__main__":
    print("=== FDE Loss Surface Visualization ===")
    train_with_surface(num_epochs=3, lambda_clean=1.0, lambda_adv=1.0)

    # 你可以立刻试下面三行测试：
    # train_with_surface(num_epochs=3, lambda_clean=5.0, lambda_adv=1.0)
    # train_with_surface(num_epochs=3, lambda_clean=1.0, lambda_adv=5.0)
    # train_with_surface(num_epochs=3, lambda_clean=0.1, lambda_adv=1.0)
