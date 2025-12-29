
import torch
import torch.nn as nn
import torch.nn.functional as F


class Discriminator(nn.Module):
    """
    PatchGAN 风格的 Discriminator，用于判别输出是否“真实 / 干净”。

    输入:
        x: (B, in_ch, H, W)
           例如:
             - in_ch = 1: 只输入 denoised image
             - in_ch = 2: concat(noisy, denoised) 形成 2 通道

    输出:
        pred: (B, 1, H_patch, W_patch)
        （patch-wise 的 “realness” score，可做 MSE / BCE）
    """

    def __init__(self, in_ch: int = 1, base_ch: int = 64):
        super().__init__()

        # C64
        self.conv1 = nn.Conv2d(in_ch, base_ch, kernel_size=4, stride=2, padding=1)
        # C128
        self.conv2 = nn.Conv2d(base_ch, base_ch * 2, kernel_size=4, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(base_ch * 2)
        # C256
        self.conv3 = nn.Conv2d(base_ch * 2, base_ch * 4, kernel_size=4, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(base_ch * 4)
        # C512
        self.conv4 = nn.Conv2d(base_ch * 4, base_ch * 8, kernel_size=4, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(base_ch * 8)

        # 输出 1 通道 patch score
        self.conv_out = nn.Conv2d(base_ch * 8, 1, kernel_size=4, stride=1, padding=1)

        self.leaky = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, in_ch, H, W)
        return: (B, 1, H_out, W_out)
        """
        h1 = self.leaky(self.conv1(x))          # (B, 64,   H/2,   W/2)
        h2 = self.leaky(self.bn2(self.conv2(h1)))  # (B, 128,  H/4,   W/4)
        h3 = self.leaky(self.bn3(self.conv3(h2)))  # (B, 256,  H/8,   W/8)
        h4 = self.leaky(self.bn4(self.conv4(h3)))  # (B, 512,  H/8-?, W/8-?)

        out = self.conv_out(h4)                 # (B, 1, H_patch, W_patch)

        # 通常 GAN 里不加 sigmoid，直接用 BCEWithLogitsLoss / MSE
        return out
