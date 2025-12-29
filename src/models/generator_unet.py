
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    """
    标准 conv 块：Conv -> BN -> ReLU -> Conv -> BN -> ReLU
    """

    def __init__(self, in_c: int, out_c: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),

            nn.Conv2d(out_c, out_c, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UpBlock(nn.Module):
    """
    上采样块：ConvTranspose2d upsample + skip 连接 + ConvBlock
    """

    def __init__(self, in_c: int, out_c: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_c, out_c, kernel_size=2, stride=2)
        # 拼接 skip 后，channel 会是 out_c + skip_c，所以 conv 的 in_c 要等于两者之和
        self.conv = ConvBlock(in_c, out_c)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)

        # 对齐 spatial 维度（防止奇数尺寸）
        if x.size()[2:] != skip.size()[2:]:
            diffY = skip.size(2) - x.size(2)
            diffX = skip.size(3) - x.size(3)
            x = F.pad(
                x,
                [diffX // 2, diffX - diffX // 2,
                 diffY // 2, diffY - diffY // 2],
            )

        # U-Net skip 拼接
        x = torch.cat([skip, x], dim=1)
        return self.conv(x)


class GeneratorUNet(nn.Module):
    """
    FDE / Denoising 用的 U-Net 型 G

    输入:
        x_noisy: (B, in_ch, H, W)
    输出:
        x_denoised: (B, out_ch, H, W)

    结构:
        encoder: 3 层 down + bottleneck
        decoder: 3 层 up + skip
        output: 1x1 conv + global residual: x_noisy + residual
    """

    def __init__(self, in_ch: int = 1, out_ch: int = 1, base_ch: int = 64):
        super().__init__()

        # Encoder
        self.enc1 = ConvBlock(in_ch, base_ch)
        self.pool1 = nn.MaxPool2d(2)

        self.enc2 = ConvBlock(base_ch, base_ch * 2)
        self.pool2 = nn.MaxPool2d(2)

        self.enc3 = ConvBlock(base_ch * 2, base_ch * 4)
        self.pool3 = nn.MaxPool2d(2)

        # Bottleneck
        self.bottleneck = ConvBlock(base_ch * 4, base_ch * 8)

        # Decoder
        self.up3 = UpBlock(base_ch * 8, base_ch * 4)
        self.up2 = UpBlock(base_ch * 4, base_ch * 2)
        self.up1 = UpBlock(base_ch * 2, base_ch)

        # 输出层
        self.out_conv = nn.Conv2d(base_ch, out_ch, kernel_size=1)

    def forward(self, x_noisy: torch.Tensor) -> torch.Tensor:
        # Encoder
        x1 = self.enc1(x_noisy)          # (B, base,   H,   W)
        x2 = self.enc2(self.pool1(x1))   # (B, 2base, H/2, W/2)
        x3 = self.enc3(self.pool2(x2))   # (B, 4base, H/4, W/4)
        x4 = self.bottleneck(self.pool3(x3))  # (B, 8base, H/8, W/8)

        # Decoder + skip
        d3 = self.up3(x4, x3)            # (B, 4base, H/4, W/4)
        d2 = self.up2(d3, x2)            # (B, 2base, H/2, W/2)
        d1 = self.up1(d2, x1)            # (B, base,  H,   W)

        residual = self.out_conv(d1)     # (B, out_ch, H, W)

        # Global residual：学 residual，然后加回 noisy
        # 如果 in_ch != out_ch，需要在外面处理通道匹配，这里默认相同
        out = x_noisy + residual
        return out
