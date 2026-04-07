import sys
import json
import warnings
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 忽略烦人的 sklearn 警告
warnings.filterwarnings('ignore')

# ==========================================
# 1. 定义 GAN 网络架构
# ==========================================
class Encoder(nn.Module):
    def __init__(self, input_dim, latent_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.2),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, latent_dim)
        )

    def forward(self, x):
        return self.net(x)

class Decoder(nn.Module):
    def __init__(self, latent_dim, output_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, output_dim)
        )

    def forward(self, x):
        return self.net(x)

class Discriminator(nn.Module):
    def __init__(self, latent_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.net(x)

# ==========================================
# 2. 核心训练与聚类逻辑
# ==========================================
def run_subtype_gan(data_path, n_clusters):
    try:
        # 1. 读取数据
        # 假设 CSV 行是样本，列是特征。自动过滤掉包含字符串的列(如样本名)
        df = pd.read_csv(data_path)
        X_raw = df.select_dtypes(include=[np.number]).values
        
        if X_raw.shape[0] == 0 or X_raw.shape[1] == 0:
            raise ValueError("CSV 文件中没有找到有效的数值型组学特征矩阵。")

        # 2. 数据标准化 (对神经网络至关重要)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)
        X_tensor = torch.FloatTensor(X_scaled)

        # 3. 超参数与设备配置
        input_dim = X_tensor.shape[1]
        latent_dim = min(64, input_dim // 2)  # 防止潜变量维度大于特征数
        batch_size = min(32, X_tensor.shape[0]) # 防止样本过少报错
        epochs = 100 # 可根据需要在前端变为可调参数
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 4. 初始化模型
        encoder = Encoder(input_dim, latent_dim).to(device)
        decoder = Decoder(latent_dim, input_dim).to(device)
        discriminator = Discriminator(latent_dim).to(device)

        opt_enc_dec = optim.Adam(list(encoder.parameters()) + list(decoder.parameters()), lr=1e-3)
        opt_disc = optim.Adam(discriminator.parameters(), lr=1e-4)

        criterion_recon = nn.MSELoss()
        criterion_gan = nn.BCELoss()

        # 5. 构建 DataLoader
        dataset = TensorDataset(X_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        X_tensor = X_tensor.to(device)

        # 6. 对抗训练循环
        encoder.train()
        decoder.train()
        discriminator.train()

        for epoch in range(epochs):
            for batch in dataloader:
                real_data = batch[0].to(device)
                b_size = real_data.size(0)

                # --- 阶段 1: 训练判别器 ---
                opt_disc.zero_grad()
                
                # 真实潜空间分布 (先验假设为标准正态分布)
                z_real = torch.randn((b_size, latent_dim)).to(device)
                # 生成的潜空间特征
                z_fake = encoder(real_data).detach()

                loss_d_real = criterion_gan(discriminator(z_real), torch.ones(b_size, 1).to(device))
                loss_d_fake = criterion_gan(discriminator(z_fake), torch.zeros(b_size, 1).to(device))
                
                loss_d = loss_d_real + loss_d_fake
                loss_d.backward()
                opt_disc.step()

                # --- 阶段 2: 训练生成器 (Encoder) 和重构器 (Decoder) ---
                opt_enc_dec.zero_grad()
                
                z_fake = encoder(real_data)
                recon_data = decoder(z_fake)
                
                # 重构损失：保证潜空间能保留原始组学信息的关键特征
                loss_recon = criterion_recon(recon_data, real_data)
                # 生成损失：欺骗判别器，使潜空间分布符合正态分布
                loss_g = criterion_gan(discriminator(z_fake), torch.ones(b_size, 1).to(device))
                
                # 综合损失 (权重比例可调，此处重构占主导)
                loss_total = 0.9 * loss_recon + 0.1 * loss_g
                loss_total.backward()
                opt_enc_dec.step()

        # 7. 提取特征并聚类
        encoder.eval()
        with torch.no_grad():
            latent_features = encoder(X_tensor).cpu().numpy()

        # 在低维潜空间运行 K-Means
        kmeans = KMeans(n_clusters=n_clusters, n_init=20, random_state=42)
        labels = kmeans.fit_predict(latent_features)

        # 8. 返回标准 JSON 供 FastAPI 解析
        output = {
            "status": "success",
            "labels": labels.tolist(),
            "algorithm": "Subtype-GAN (Adversarial Autoencoder)"
        }
        print(json.dumps(output))

    except Exception as e:
        # 任何错误都会以 JSON 格式打印，确保 server.py 能捕获而非崩溃
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }))

# ==========================================
# 3. 命令行入口
# ==========================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({
            "status": "error", 
            "message": "参数不足：请提供数据路径和聚类数量"
        }))
        sys.exit(1)

    csv_path = sys.argv[1]
    clusters = int(sys.argv[2])
    
    run_subtype_gan(csv_path, clusters)