
"""
train_gan_fde.py

Joint training script for:
- GeneratorUNet (G): denoiser / reconstruction network
- Discriminator (D): PatchGAN-style real/fake discriminator
- FDEClassifier (C): classifier head (FDE "battlefield" model)

+ Loss surface visualization for classifier C using LossSurfaceExplorer.
"""
import os
from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from models import GeneratorUNet, Discriminator, FDEClassifier
from utils.loss_surface_adapter import LossSurfaceExplorer

device = "cuda" if torch.cuda.is_available() else "cpu"


def get_fake_batch(
    batch_size: int = 16,
    img_size: int = 64,
    num_classes: int = 10,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    返回:
        x_noisy: (B, 1, H, W)
        x_clean: (B, 1, H, W)
        y      : (B,)
    这里用随机数据占位：x_clean ~ U(0,1), x_noisy = x_clean + noise
    """
    x_clean = torch.rand(batch_size, 1, img_size, img_size, device=device)
    noise = 0.1 * torch.randn_like(x_clean)
    x_noisy = torch.clamp(x_clean + noise, 0.0, 1.0)
    y = torch.randint(0, num_classes, (batch_size,), device=device)
    return x_noisy, x_clean, y


def train_gan_fde(
    num_epochs: int = 5,
    img_size: int = 64,
    num_classes: int = 10,
    lambda_recon: float = 1.0,
    lambda_adv: float = 0.01,
    lambda_cls: float = 1.0,
    gamma_clean: float = 1.0,
    gamma_denoised: float = 1.0,
    lr_g: float = 1e-4,
    lr_d: float = 4e-4,
    lr_c: float = 1e-4,
    save_dir: str = "checkpoints_gan_fde",
):
    os.makedirs(save_dir, exist_ok=True)

    # --------- 模型 ---------
    G = GeneratorUNet(in_ch=1, out_ch=1, base_ch=64).to(device)
    D = Discriminator(in_ch=1, base_ch=64).to(device)
    C = FDEClassifier(in_ch=1, num_classes=num_classes).to(device)

    # --------- 优化器 ---------
    opt_G = torch.optim.Adam(G.parameters(), lr=lr_g, betas=(0.5, 0.999))
    opt_D = torch.optim.Adam(D.parameters(), lr=lr_d, betas=(0.5, 0.999))
    opt_C = torch.optim.Adam(C.parameters(), lr=lr_c)

    # --------- 损失函数 ---------
    bce_logits = nn.BCEWithLogitsLoss()
    mse_loss = nn.MSELoss()
    ce_loss = nn.CrossEntropyLoss()

    # --------- Loss surface explorer for C ---------
    # 这里我们先看 C 在 clean 图像上的 CE loss surface，
    # 你之后可以改成 clean+denoised 组合。
    def cls_surface_loss_fn(model: nn.Module, batch):
        x_clean, y = batch
        x_clean = x_clean.to(device)
        y = y.to(device)
        logits = model(x_clean)
        return ce_loss(logits, y)

    explorer_C = LossSurfaceExplorer(C, cls_surface_loss_fn, device=device)

    print("=== Start GAN + FDE joint training (with C loss surface) ===")
    print(f"device={device}, img_size={img_size}, num_classes={num_classes}")
    print(
        f"lambda_recon={lambda_recon}, lambda_adv={lambda_adv}, "
        f"lambda_cls={lambda_cls}, gamma_clean={gamma_clean}, gamma_denoised={gamma_denoised}"
    )

    for epoch in range(1, num_epochs + 1):
        G.train()
        D.train()
        C.train()

        # ===== 取一个 batch =====
        x_noisy, x_clean, y = get_fake_batch(
            batch_size=32,
            img_size=img_size,
            num_classes=num_classes,
        )

        # =================================================
        # 1) 更新 Discriminator
        # =================================================
        opt_D.zero_grad()
        pred_real = D(x_clean)
        valid = torch.ones_like(pred_real, device=device)
        loss_D_real = bce_logits(pred_real, valid)

        with torch.no_grad():
            x_denoised_for_D = G(x_noisy)
        pred_fake = D(x_denoised_for_D)
        fake = torch.zeros_like(pred_fake, device=device)
        loss_D_fake = bce_logits(pred_fake, fake)

        loss_D = 0.5 * (loss_D_real + loss_D_fake)
        loss_D.backward()
        opt_D.step()

        # =================================================
        # 2) 更新 Generator (G)
        # =================================================
        opt_G.zero_grad()
        x_denoised = G(x_noisy)

        # Reconstruction
        loss_recon = mse_loss(x_denoised, x_clean)

        # GAN adv
        pred_fake_for_G = D(x_denoised)
        valid_for_G = torch.ones_like(pred_fake_for_G, device=device)
        loss_adv_G = bce_logits(pred_fake_for_G, valid_for_G)

        # Classification consistency on denoised
        logits_denoised = C(x_denoised)
        loss_cls = ce_loss(logits_denoised, y)

        loss_G = (
            lambda_recon * loss_recon
            + lambda_adv * loss_adv_G
            + lambda_cls * loss_cls
        )
        loss_G.backward()
        opt_G.step()

        # =================================================
        # 3) 更新 Classifier (C)
        # =================================================
        opt_C.zero_grad()
        logits_clean = C(x_clean)
        loss_C_clean = ce_loss(logits_clean, y)

        with torch.no_grad():
            x_denoised_detach = x_denoised.detach()
        logits_denoised_detach = C(x_denoised_detach)
        loss_C_denoised = ce_loss(logits_denoised_detach, y)

        loss_C = (
            gamma_clean * loss_C_clean
            + gamma_denoised * loss_C_denoised
        )
        loss_C.backward()
        opt_C.step()

        # --------- 日志 ---------
        print(
            f"[Epoch {epoch:03d}] "
            f"D: {loss_D.item():.4f} | "
            f"G_recon: {loss_recon.item():.4f} | "
            f"G_adv: {loss_adv_G.item():.4f} | "
            f"G_cls: {loss_cls.item():.4f} | "
            f"C: {loss_C.item():.4f}"
        )

        # --------- 保存权重 ---------
        torch.save(G.state_dict(), os.path.join(save_dir, f"G_epoch{epoch}.pt"))
        torch.save(D.state_dict(), os.path.join(save_dir, f"D_epoch{epoch}.pt"))
        torch.save(C.state_dict(), os.path.join(save_dir, f"C_epoch{epoch}.pt"))

        
        if epoch in [1, num_epochs]:
            # 用一个新的 batch（只传 clean + y）
            _, x_clean_vis, y_vis = get_fake_batch(
                batch_size=32,
                img_size=img_size,
                num_classes=num_classes,
            )
            batch_vis = (x_clean_vis, y_vis)
            title = f"C loss surface at epoch {epoch}"
            explorer_C.plot_2d_surface(
                batch_vis,
                radius=0.5,
                grid_size=21,
                title=title,
            )

    print("=== Training finished ===")


if __name__ == "__main__":
    train_gan_fde(
        num_epochs=5,
        img_size=64,
        num_classes=10,
        lambda_recon=1.0,
        lambda_adv=0.01,
        lambda_cls=1.0,
        gamma_clean=1.0,
        gamma_denoised=1.0,
        lr_g=1e-4,
        lr_d=4e-4,
        lr_c=1e-4,
        save_dir="checkpoints_gan_fde",
    )
