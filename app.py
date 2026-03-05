import os
import streamlit as st
from dotenv import load_dotenv
import dashscope
from dashscope import Generation
import PyPDF2
import plotly.graph_objects as go
from collections import Counter
import sqlite3
import bcrypt
import json
import datetime
import streamlit_authenticator as stauth
import smtplib
from email.message import EmailMessage
import secrets
import string

# ============ 配置与环境变量 ================
load_dotenv()
API_KEY = os.getenv("ALIYUN_API_KEY")
dashscope.api_key = API_KEY
EMAIL_SENDER = os.getenv("EMAIL_SENDER", None)  # 发件邮箱（如需忘记密码功能）
EMAIL_PASS = os.getenv("EMAIL_PASS", None)      # 邮箱授权码

DB_PATH = "users.db"

st.set_page_config(page_title="AI合同风险雷达", layout="wide")
st.title("🛡️ AI合同风险雷达")
st.markdown("上传您的合同，智能识别风险，并生成可视化报告。（登录后可用 • 支持注册/找回/改密）")

# ===================== 数据库相关 =======================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        last_login DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        contract_name TEXT NOT NULL,
        analysis_result TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def add_user(username, email, password):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, email, password, created_at) VALUES (?,?,?,?)',
                  (username, email, pw_hash, datetime.datetime.now()))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, password FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[1]):
        return row[0]  # user_id
    return None

def update_last_login(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET last_login=? WHERE id=?', (datetime.datetime.now(), user_id))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email=?', (email,))
    row = c.fetchone()
    conn.close()
    return row

def get_user_by_username(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row

def update_user_password(email, new_password):
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET password=? WHERE email=?', (pw_hash, email))
    conn.commit()
    conn.close()

def insert_history(user_id, contract_name, analysis_result):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO history (user_id, contract_name, analysis_result, created_at) VALUES (?, ?, ?, ?)',
              (user_id, contract_name, json.dumps(analysis_result, ensure_ascii=False), datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=10):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT id, contract_name, analysis_result, created_at FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT ?', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "contract_name": r[1],
        "result": json.loads(r[2]),
        "created_at": r[3]
    } for r in rows]

def update_username(user_id, new_username):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET username=? WHERE id=?', (new_username, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ================ 邮件发送（用于重置密码） ===================
def send_email(to_email, subject, content):
    if not EMAIL_SENDER or not EMAIL_PASS:
        st.warning("未配置邮箱发送功能（EMAIL_SENDER/EMAIL_PASS 未设置）")
        return False
    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    try:
        # 支持SMTP SSL/普通登录（以QQ邮箱为例，支持smtp.qq.com:465, 587等）
        with smtplib.SMTP_SSL("smtp.qq.com", 465) if EMAIL_SENDER.endswith("qq.com") else smtplib.SMTP("smtp.163.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"邮件发送失败: {e}")
        return False

def gen_temp_password(n=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

# ================ 认证/注册/忘记密码/改密 ===============
def show_login():
    st.subheader("用户登录")
    login_username = st.text_input("用户名")
    login_password = st.text_input("密码", type="password")
    if st.button("登录"):
        user_id = authenticate_user(login_username, login_password)
        if user_id:
            st.session_state['user_id'] = user_id
            update_last_login(user_id)
            st.success("登录成功")
            st.session_state['run_main'] = True
            st.rerun()
        else:
            st.error("用户名或密码错误")
    st.caption("[注册账号](#注册账号) | [忘记密码](#忘记密码)")

def show_register():
    st.subheader("注册账号")
    username = st.text_input("用户名（必填，4-20字符）", key="reg_user")
    email = st.text_input("邮箱（用于找回密码）", key="reg_mail")
    pw = st.text_input("密码（至少6位）", type="password", key="reg_pw")
    pw2 = st.text_input("确认密码", type="password", key="reg_pw2")
    if st.button("注册"):
        if not username or not email or not pw or not pw2:
            st.warning("所有字段必填")
        elif len(username) < 4 or len(username) > 20 or " " in username:
            st.warning("用户名4~20字符且不能有空格")
        elif "@" not in email or "." not in email:
            st.warning("邮箱填写不正确！")
        elif pw != pw2:
            st.warning("两次输入密码不一致")
        elif len(pw) < 6:
            st.warning("密码至少6位")
        elif get_user_by_username(username):
            st.error("用户名已存在")
        elif get_user_by_email(email):
            st.error("该邮箱已注册")
        else:
            ok, msg = add_user(username, email, pw)
            if ok:
                st.success("注册成功，请登录")
                st.session_state['show_login'] = True
                st.rerun()
            else:
                st.error(f"注册失败: {msg}")

def show_forget():
    st.subheader("忘记密码")
    email = st.text_input("请输入注册邮箱")
    if st.button("发送重置密码邮件"):
        user = get_user_by_email(email)
        if not user:
            st.error("邮箱未注册！")
        else:
            temp_new_pw = gen_temp_password()
            update_user_password(email, temp_new_pw)
            content = f"您的AI合同风险雷达临时密码为：{temp_new_pw}\n请尽快登录并修改密码！"
            email_sent = send_email(email, "AI合同风险雷达-重置密码", content)
            if email_sent:
                st.success("重置密码已发送到您的邮箱，请查收")
            else:
                st.error("重置邮件发送失败，请联系管理员")

def show_change_pw(user_id):
    st.subheader("修改密码")
    old_pw = st.text_input("原密码", type="password", key="chg_old")
    new_pw = st.text_input("新密码", type="password", key="chg_new")
    new_pw2 = st.text_input("确认新密码", type="password", key="chg_new2")
    if st.button("提交修改"):
        # 获取用户原始哈希
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT password, email FROM users WHERE id=?', (user_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            st.error("用户不存在")
        elif not bcrypt.checkpw(old_pw.encode(), row[0]):
            st.error("原密码错误")
        elif new_pw != new_pw2:
            st.error("新密码两次不一致")
        elif len(new_pw) < 6:
            st.error("新密码至少6位")
        else:
            update_user_password(row[1], new_pw)
            st.success("密码修改成功，请重新登录")
            st.session_state.clear()
            st.rerun()

# ================ 合同分析核心功能 ================

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    else:
        return uploaded_file.read().decode('utf-8', errors='ignore')

def risk_severity_color(severity):
    if severity == "high":
        return "red"
    if severity == "mid":
        return "orange"
    return "green"

def gen_radar_chart(dimensions):
    labels = list(dimensions.keys())
    values = list(dimensions.values())
    values += values[:1]
    labels += labels[:1]
    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values,
                theta=labels,
                fill='toself',
                marker=dict(color='rgba(255, 99, 71, 0.7)')
            )
        ]
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30)
    )
    return fig

def gen_bar_chart(risk_points):
    cnt = Counter([r["severity"] for r in risk_points])
    levels = ['high', 'mid', 'low']
    values = [cnt.get(lv, 0) for lv in levels]
    fig = go.Figure(
        [go.Bar(x=['高风险', '中风险', '低风险'], y=values, marker_color=["red", "orange", "green"])]
    )
    fig.update_layout(
        yaxis_title="风险点数量",
        margin=dict(l=30, r=30, t=30, b=30)
    )
    return fig

def ai_contract_analysis(text):  # 用户已认证
    prompt = f"""你是一名合同风险分析专家。请严格按照如下JSON格式输出：
{{
  "total_score": 整数 (0-100),
  "risk_points": [
    {{"clause": "风险条款原文或位置描述", "reason": "为什么这是风险，具体说明", "severity": "high/mid/low"}}
  ],
  "dimensions": {{
    "权利义务": 0-100,
    "违约责任": 0-100,
    "模糊条款": 0-100,
    "合规风险": 0-100,
    "缺失条款": 0-100
  }},
  "summary": "总体风险评估摘要"
}}
要求：high ≥70分, mid 40~69分, low ≤39分，风险点不宜过少，每个风险有专属reason。
合同内容如下：
{text}
"""
    response = Generation.call(
        model='qwen-plus',
        prompt=prompt,
        result_format='message',
        temperature=0.1,
    )
    import re
    content = response.output.choices[0].message.content
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        content = match.group(0)
    try:
        result = json.loads(content)
    except Exception:
        st.error("AI返回结果无法解析为JSON，请重试。")
        return None
    return result

def get_report_txt(filename, result):
    lines = []
    lines.append(f"合同文件: {filename}")
    lines.append(f"风险总评分: {result['total_score']} 分")
    lines.append("维度分:\n" + "\n".join([f"- {k}: {v}分" for k, v in result['dimensions'].items()]))
    lines.append("\n详细风险点：")
    for idx, rp in enumerate(result['risk_points'], 1):
        lines.append(f"{idx}. 条款: {rp['clause']}\n   原因: {rp['reason']}\n   风险等级: {rp['severity']}")
    lines.append("\n总体总结：\n" + result['summary'])
    return "\n".join(lines)

# ============ 主逻辑入口 ==============
def main():
    st.sidebar.title("导航")
    page = st.sidebar.radio("功能选择", ("合同分析", "修改密码", "退出登录"))
    user_id = st.session_state['user_id']

    if page == "退出登录":
        st.session_state.clear()
        st.success("已注销登录，请刷新页面或重新登录。")
        st.stop()

    # 历史记录
    history = get_user_history(user_id)
    with st.sidebar:
        st.header("🔎 我的分析记录")
        for idx, record in enumerate(history):
            show_name = f"{record['contract_name']} ({record['result'].get('total_score','-')}分)"
            if st.button(show_name, key=f"hist_{idx}"):
                st.session_state['selected_history'] = idx

    if page == "修改密码":
        show_change_pw(user_id)
        return

    # 合同主体操作
    uploaded_file = st.file_uploader("上传合同文件（TXT/PDF，仅限中文文本合同）", type=['txt', 'pdf'])
    view_idx = st.session_state.get('selected_history')
    if uploaded_file:
        file_text = extract_text_from_file(uploaded_file)
        with st.expander("显示原始合同文本", expanded=False):
            st.code(file_text[:2000] + ('...' if len(file_text) > 2000 else ''), language='text')
        if st.button("点击进行AI合同风险分析", type="primary"):
            with st.spinner("AI分析中..."):
                result = ai_contract_analysis(file_text)
            if result:
                insert_history(user_id, uploaded_file.name, result)
                st.session_state['selected_history'] = 0
                st.success("分析完成, 已保存到历史记录。")
                st.rerun()
    # 展示历史/本次报告
    if view_idx is not None and 0 <= view_idx < len(history):
        record = history[view_idx]
        filename = record.get("contract_name", "--")
        result = record.get("result", {})
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("风险评分")
            score = result.get("total_score")
            st.metric("风险总分", value=f"{score if score is not None else '-'} 分")
            st.caption("分数越高风险越大")

        with col2:
            st.subheader("维度雷达图")
            dimensions = result.get("dimensions", {})
            if dimensions:
                fig_radar = gen_radar_chart(dimensions)
                st.plotly_chart(fig_radar, use_container_width=True)

        st.subheader("风险点数量柱状图")
        risk_points = result.get("risk_points", [])
        if risk_points:
            fig_bar = gen_bar_chart(risk_points)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("详细风险条款[条款/原因/等级]")
        for rp in risk_points:
            color = risk_severity_color(rp['severity'])
            st.markdown(
                f"<div style='border-left:6px solid {color}; padding-left:10px; margin-bottom:10px;'>"
                f"<b>条款：</b>{rp['clause']}<br>"
                f"<b>原因：</b>{rp['reason']}<br>"
                f"<b>风险等级：</b><span style='color:{color}'>{rp['severity']}</span>"
                "</div>",
                unsafe_allow_html=True
            )
        st.subheader("AI总结")
        st.info(result.get("summary","无"))

        report_txt = get_report_txt(filename, result)
        st.download_button(
            label="下载报告TXT",
            data=report_txt.encode('utf-8'),
            file_name=f"{filename}_风险分析报告.txt",
            mime="text/plain"
        )

# ============= 页面路由管理 ============
def show_auth_router():
    menu = st.sidebar.selectbox(
        "认证相关", ["登录", "注册账号", "忘记密码"])

    if menu == "登录" or st.session_state.get('show_login'):
        st.session_state['show_login'] = False
        show_login()
    elif menu == "注册账号":
        show_register()
    elif menu == "忘记密码":
        show_forget()

if __name__ == "__main__" or True:
    create_tables()
    # 认证入口
    if 'user_id' in st.session_state and st.session_state['user_id']:
        try:
            main()
        except Exception as e:
            st.exception(e)
    else:
        show_auth_router()
