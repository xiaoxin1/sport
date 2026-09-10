# 苏州外国语学校运动会系统（SFLS）

面向学校运动会筹备、报名、编排与成绩统计的管理平台。

## 技术架构

- 前端：React + TypeScript + Vite
- 后端：Python FastAPI + SQLAlchemy
- 数据库：MySQL 8（Docker 内置）
- 部署：Docker Compose，统一通过 `8686` 端口访问

## 启动

```bash
copy .env.example .env
docker compose up --build
```

访问 `http://localhost:8686`。初始管理员账号为 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`（默认 `admin` / `SFLS2026!`）。

## 本次需求与改动（2026-09-09）

- 建立 Docker 化的 React、FastAPI、MySQL 三层项目架构。
- 完成管理员登录、会话鉴权、学年及运动会日期设置。
- 完成项目配置、班级报名和号码生成的可操作 API 与管理界面。
- 建立竞赛日程、项目分组、最高记录、秩序册、成绩及积分统计模块入口与数据模型。
- 提供 DeepSeek API 配置项；排程算法与 AI 多轮调优将在确认具体场地/项目规则后接入。
- 修复 Nginx 未设置静态资源根目录导致首页重定向循环并返回 HTTP 500 的问题。

## 目录

`backend/` 为 FastAPI 业务服务，`frontend/` 为 React 管理控制台。生产环境必须修改 `.env` 的数据库密码、JWT 密钥和管理员密码。
