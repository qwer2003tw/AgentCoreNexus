# Python 3.12 部署問題

**問題**: 系統環境不支持 Python 3.12 構建

---

## 🚨 當前狀況

### 錯誤 1：缺少 Python 3.12
```
Binary validation failed for python, searched for python in following locations: ['/usr/bin/python3'] 
which did not satisfy constraints for runtime: python3.12
```

### 錯誤 2：缺少 Docker
```
Running AWS SAM projects locally requires a container runtime. 
Do you have Docker or Finch installed and running?
```

---

## 💡 解決方案（3 選 1）

### 選項 A：安裝 Python 3.12（推薦，20-30 分鐘）

#### Amazon Linux 2023
```bash
# Python 3.12 應該在 repo 中
sudo yum install python3.12 -y
python3.12 --version
```

#### Amazon Linux 2（需要額外 repo）
```bash
# 添加 EPEL repo
sudo amazon-linux-extras install epel -y

# 或從源碼編譯（30-45 分鐘）
sudo yum install gcc openssl-devel bzip2-devel libffi-devel -y
cd /tmp
wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz
tar xzf Python-3.12.0.tgz
cd Python-3.12.0
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall
python3.12 --version
```

**驗證**：
```bash
which python3.12
python3.12 --version  # 應該顯示 3.12.x
```

---

### 選項 B：安裝 Docker（推薦，10-15 分鐘）

```bash
# Amazon Linux 2
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# 重新登入或使用 newgrp
newgrp docker

# 驗證
docker --version
docker ps
```

**使用**：
```bash
sam build --use-container  # 在 Docker 中構建
```

**優點**：
- 構建環境與 Lambda 完全一致
- 避免本地環境差異
- 推薦用於生產部署

---

### 選項 C：暫時回退到 Python 3.11（快速，5 分鐘）

**不推薦**，但如果急需部署：

```bash
# 回退配置
git revert HEAD  # 回退到 Python 3.11 配置
make deploy-all  # 部署

# 之後再升級（準備好環境後）
```

---

## 📋 推薦執行順序

### 步驟 1：安裝 Docker（最簡單）
```bash
sudo yum install docker -y
sudo systemctl start docker
sudo usermod -a -G docker $USER
newgrp docker
```

### 步驟 2：重新部署
```bash
cd /home/ec2-user/Projects/AgentCoreNexus
make deploy-all
```

---

## ✅ 我的建議

**安裝 Docker**（選項 B），因為：
- ✅ 安裝快速（10-15 分鐘）
- ✅ 未來所有部署都更可靠
- ✅ 構建環境與 Lambda 一致
- ✅ AWS 官方推薦做法

---

**等待用戶選擇並準備環境...**