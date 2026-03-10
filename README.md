# 智能合同审计系统 (AI Contract Radar)

## 📊 版本演进

### V2 - Agentic RAG 架构（当前版本）
- **核心架构**：基于 ReAct 框架的智能体，能自主规划审计路径
- **RAG 知识库**：Pinecone 向量数据库存储历史合同，混合检索相似条款
- **智能分析**：AI 自动拆解任务、调用工具、生成报告
- **可视化溯源**：风险热力图 + 参考条款展示，结果可追溯
- **技术栈**：Streamlit + 通义千问 + Pinecone + Plotly

### V1 - 基础版本
- 单次对话式合同分析
- 基础风险评分和雷达图
- 用户系统与历史记录

## 🚀 在线体验
- **V2 版本**：[你的 v2 应用链接]
- **V1 版本**：[你的 v1 应用链接]（如已部署）

## 🛠️ 技术架构
![架构图](link-to-your-architecture-diagram)

## 📝 核心功能
- 用户注册/登录，历史记录保存
- 上传 PDF/TXT 合同，自动提取文本
- Agent 自主规划：识别条款类型 → 检索历史案例 → 对比分析 → 生成报告
- 风险可视化：总分、维度雷达图、风险点柱状图
- 参考条款溯源：每条风险点附带相似历史条款

## 🔧 本地运行
```bash
git clone https://github.com/YourUsername/ai-contract-radar.git
cd ai-contract-radar
pip install -r requirements.txt
streamlit run app.py
```

## 📁 环境变量配置
创建 `.env` 文件：
```
ALIYUN_API_KEY=你的阿里云密钥
PINECONE_API_KEY=你的Pinecone密钥
PINECONE_ENV=us-east1-aws
PINECONE_INDEX=contract-rag
EMAIL_SENDER=你的邮箱
EMAIL_PASS=邮箱授权码
```

## 📄 License
MIT