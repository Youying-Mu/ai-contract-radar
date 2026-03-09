# AI合同风险雷达 ⚖️

> 1分钟，让AI律师帮你审合同，小白也能看懂风险

## 🚀 在线体验
[点击这里试用](https://ai-contract-radar.streamlit.app)（无需安装，浏览器打开即可）

## 📸 功能截图（登录页、上传界面、雷达图、详细风险条款）
<img width="1295" height="600" alt="登录" src="https://github.com/user-attachments/assets/957549e8-41bb-41ff-9d50-ae5d8ae6e6ff" />
<img width="1299" height="549" alt="上传界面" src="https://github.com/user-attachments/assets/317ed762-fcaa-413a-8406-f1fa53496ea6" />
<img width="1239" height="615" alt="雷达图" src="https://github.com/user-attachments/assets/811513c7-3a21-464a-b2d3-e0301bdf0b1c" />
<img width="1238" height="946" alt="详细风险条款" src="https://github.com/user-attachments/assets/a91c112d-9db5-4f65-bf61-222bfdefc3d0" />


## ✨ 核心功能
- ✅ 用户系统（注册/登录、密码加密、修改密码）
- ✅ 上传合同（TXT/PDF）
- ✅ AI自动分析风险条款（阿里云通义千问Plus）
- ✅ 风险量化评分（0-100分，分数越高风险越大）
- ✅ 可视化图表（5大风险维度雷达图+ 风险等级分布柱状图）
- ✅ 详细风险点列表（逐条列出条款原文、风险原因、风险等级）
- ✅ 历史记录保存（按用户隔离）
- ✅ 报告下载（TXT格式）

## 🛠️ 技术栈
- **前端/后端**：Streamlit
- **AI模型**：阿里云通义千问Plus
- **数据库**：SQLite
- **可视化**：Plotly
- **认证**：bcrypt密码加密
- **部署**：Streamlit Cloud

## 📦 本地运行
```bash
# 克隆仓库
git clone https://github.com/Youying-Mu/ai-contract-radar.git
cd ai-contract-radar

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
echo "ALIYUN_API_KEY=你的密钥" > .env

# 运行
# 方法一（推荐，需确保 streamlit 在 PATH 中）
streamlit run app.py

# 方法二（如果提示 streamlit 不是命令，用这个）
python -m streamlit run app.py
