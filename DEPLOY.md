# 发布到 GitHub 完整指南

> 本文件记录了把「手游 A/B 实验与留存归因分析」作品集发布到 GitHub 并在线展示的全部步骤。
> 项目目录：`C:\Users\Sheona\WorkBuddy\2026-05-10-task-2\game-analytics-portfolio`

---

## 零、数据集来源

| 项目 | 内容 |
|------|------|
| **数据集名称** | Mobile Games A/B Testing: Cookie Cats |
| **Kaggle 链接** | https://www.kaggle.com/datasets/yufengsui/mobile-games-ab-testing |
| **提供者** | Aurelia Sui（原始数据由 Tactile Entertainment 采集并脱敏） |
| **规模** | 90,189 名玩家 × 5 字段 |
| **许可** | Kaggle 页面标注为公共数据集，可自由用于分析展示 |

本地已有副本：`data/cookie_cats.csv`（2.6 MB），**无需重新下载**。

若需重新获取：
1. 打开上面的 Kaggle 链接
2. 点击右上角 **Download → Download Dataset**
3. 解压后把 `cookie_cats.csv` 放到项目的 `data/` 目录下

---

## 一、当前准备状态（已完成）

以下步骤我已经帮你做完了，**你不需要重复执行**：

- [x] 初始化 git 仓库，主分支为 `main`
- [x] 配置项目级提交身份（`Wang Xinyu` / 占位邮箱，**建议改成你自己的**，见第二节）
- [x] 完成首次提交，commit hash：`908d3fb`，共 29 个文件
- [x] `.gitignore` 已配置：排除 `cookie_cats_clean.csv`（可由脚本重新生成）与各类缓存
- [x] 已生成 `docs/index.html`，用于 GitHub Pages 在线展示报告
- [x] README 已补充数据集来源、核心结论与部署说明

你要做的是下面**第二到第四节**。

---

## 二、改成你自己的提交身份（建议，2 分钟）

当前提交作者是一个占位身份。改成你 GitHub 账号的信息，提交记录才会关联到你的主页——**面试官点进仓库能看到是你的作品，这一点很重要**。

```bash
cd "C:\Users\Sheona\WorkBuddy\2026-05-10-task-2\game-analytics-portfolio"

# 换成你 GitHub 的用户名和邮箱
git config --local user.name "你的GitHub用户名"
git config --local user.email "你的GitHub注册邮箱"

# 重写已有提交的作者信息
git commit --amend --reset-author --no-edit
```

> **找不到邮箱？** 用 GitHub 提供的隐私邮箱最稳妥：`GitHub → Settings → Emails → Keep my email addresses private`，页面上会显示形如 `12345678+username@users.noreply.github.com` 的地址，直接用它即可。
>
> 如果不想暴露真实邮箱，务必用上面这个 noreply 地址。

---

## 三、创建远程仓库并推送

### 3.1 在 GitHub 网页创建空仓库

1. 打开 https://github.com/new
2. **Repository name** 填：`game-analytics-portfolio`
   （也可用 `game-ab-testing-analysis`，名字随你，后面命令里同步改）
3. **Description** 建议填：
   > Mobile game A/B testing analysis — retention attribution, statistical testing & churn modeling on 90,189 players
4. **Public / Private**：**必须选 Public**
   —— 私有仓库的 GitHub Pages 需要付费账号才能对外访问，而且简历里的链接招聘方打不开
5. ⚠️ **不要勾选** `Add a README file`、`.gitignore`、`license`
   —— 本地已有这些文件，勾了会产生冲突
6. 点击 **Create repository**
7. 创建后会跳到一个"Quick setup"页面，**先留着别关**，下一步要用到里面的地址

### 3.2 配置认证方式（二选一）

**方式 A：HTTPS + 访问令牌（推荐新手，最省事）**

GitHub 从 2021 年起不再接受账号密码推送，需要 Personal Access Token（PAT）：

1. 打开 https://github.com/settings/tokens
2. 点击 **Generate new token → Generate new token (classic)**
3. **Note** 随便填，比如 `workbuddy-push`
4. **Expiration** 建议选 `90 days`
5. **Scopes** 只勾选最上面那个 **`repo`**（包含全部子项）
6. 拉到底点击 **Generate token**
7. **立刻复制生成的令牌**（形如 `ghp_xxxxxxxxxxxx`）——页面刷新后就再也看不到了

推送时：
- 用户名填你的 GitHub 用户名
- 密码栏**粘贴这个令牌**（不是你的登录密码）

> Windows 上 git 会自动记住凭据，所以只需要输一次。

**方式 B：SSH 密钥（一次配置长期有效）**

```bash
# 1. 生成密钥（邮箱换成你的）
ssh-keygen -t ed25519 -C "你的GitHub邮箱"

# 2. 一路回车使用默认路径即可，然后查看公钥内容
cat ~/.ssh/id_ed25519.pub
```

把输出的整段内容（以 `ssh-ed25519` 开头）复制，然后：
1. 打开 https://github.com/settings/keys
2. 点击 **New SSH key**
3. Title 随便填，Key 粘贴刚才复制的内容，保存
4. 验证连接：

```bash
ssh -T git@github.com
# 看到 "Hi 你的用户名! You've successfully authenticated" 即成功
```

### 3.3 推送代码

在项目目录执行（**把地址换成你自己的**）：

```bash
cd "C:\Users\Sheona\WorkBuddy\2026-05-10-task-2\game-analytics-portfolio"

# 关联远程仓库
# 【方式 A 用这行】
git remote add origin https://github.com/你的用户名/game-analytics-portfolio.git
# 【方式 B 用这行】
# git remote add origin git@github.com:你的用户名/game-analytics-portfolio.git

# 推送
git push -u origin main
```

推送成功后刷新 GitHub 页面，就能看到完整的项目了。

> **如果报错 `remote origin already exists`**：说明之前加过，先删再加重试：
> ```bash
> git remote remove origin
> ```

---

## 四、开启 GitHub Pages（把报告变成可点击链接）

这一步做完，你的简历上就能直接放一个**在线报告链接**，而不是让人下载文件。

1. 进入仓库页面 → 点击 **Settings**（顶部菜单）
2. 左侧菜单找到 **Pages**
3. **Source** 选择 `Deploy from a branch`
4. **Branch** 下拉选择 `main`，右侧目录下拉选择 **`/docs`**
5. 点击 **Save**
6. 等 1–2 分钟，页面上方会出现绿色提示，链接形如：

```
https://你的用户名.github.io/game-analytics-portfolio/
```

点开就是完整的 HTML 分析报告，可以直接分享给面试官。

### 简历里怎么写这一行

```
游戏数据分析作品：https://你的用户名.github.io/game-analytics-portfolio/
基于 9 万玩家真实线上 A/B 实验数据，完成留存归因、统计检验（Z检验/Bootstrap/贝叶斯）
与流失预测建模，输出门槛调整决策建议（Lift 4.11x）
```

---

## 五、后续更新代码

改动文件后，三步提交：

```bash
cd "C:\Users\Sheona\WorkBuddy\2026-05-10-task-2\game-analytics-portfolio"
git add .
git commit -m "说明这次改了什么"
git push
```

> 重新跑过 `python src/run_all.py` 后，`docs/index.html` 不会自动更新。
> 需要手动同步，否则在线报告和最新结果不一致：
> ```bash
> cp "outputs/游戏留存与AB实验分析报告.html" docs/index.html
> git add . && git commit -m "更新报告" && git push
> ```

---

## 六、常见问题

| 问题 | 原因与解决 |
|------|-----------|
| `Authentication failed` | 密码栏不能填登录密码，必须填 PAT 令牌（见 3.2 方式 A） |
| `Support for password authentication was removed` | 同上，改用 PAT 或 SSH |
| `remote origin already exists` | `git remote remove origin` 后重新 add |
| `failed to push some refs` | 远程仓库不是空的（创建时勾了 README）。执行 `git pull --rebase origin main` 后再 push |
| Pages 打开是 404 | 再等 2–3 分钟；确认 Branch 选的是 `main` 且目录是 `/docs`；确认仓库是 Public |
| Pages 打开显示 README 而不是报告 | 目录选错了，必须是 `/docs`，因为 `docs/index.html` 才是报告 |
| 仓库体积太大 | 目前 4.7 MB，完全没问题。若担心，可把 `data/cookie_cats.csv` 也加入 `.gitignore`，改为在 README 里注明从 Kaggle 下载 |
| 忘记 GitHub 用户名 | 登录 github.com，右上角头像旁就是 |

---

## 七、可选：添加开源许可证

作品集仓库建议加一个 LICENSE，让访问者知道使用范围：

1. 仓库页面 → **Add file → Create new file**
2. 文件名填 `LICENSE`
3. 点击右上角 **Choose a license template**，选 **MIT License**（最宽松、最常见）
4. 填写年份和你的名字，提交即可

> MIT 允许他人自由使用你的代码。如果希望保留权利，可以选择 `All rights reserved` 或无许可证（默认保留全部权利）。

---

## 八、清单一览

| # | 步骤 | 耗时 | 状态 |
|---|------|------|------|
| 1 | 本地仓库初始化与首次提交 | — | ✅ 已完成 |
| 2 | 修改提交身份为你的 GitHub 账号 | 2 分钟 | ⬜ 待做 |
| 3 | 网页创建空的 Public 仓库 | 1 分钟 | ⬜ 待做 |
| 4 | 配置认证（PAT 或 SSH） | 3 分钟 | ⬜ 待做 |
| 5 | `git push -u origin main` | 1 分钟 | ⬜ 待做 |
| 6 | Settings → Pages 选 `/docs` | 2 分钟 | ⬜ 待做 |
| 7 | 把在线链接写进简历 | 1 分钟 | ⬜ 待做 |
