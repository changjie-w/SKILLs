<div align="center">

# SKILLs

**面向 Codex 的个人技能集合**

让论文阅读与算法学习更顺手。

[技能一览](#技能一览) · [安装](#安装) · [使用示例](#使用示例) · [目录结构](#目录结构)

</div>

---

## 技能一览

每个技能独立维护、按需安装。当前包含：

| 技能 | 可以帮你做什么 | 文档 |
| :--- | :--- | :--- |
| 📄 **trans** | 将英文论文制作为逐页双语 PDF：左侧英文原页，右侧可检索简体中文。支持本地 PDF 与 Zotero。 | [技能定义](skills/trans/SKILL.md) · [使用指南](skills/trans/README.md) |
| 🧠 **algo** | 从论文、教材、课程材料、代码或算法名称开始，理解算法解决的问题与工程流程。覆盖机器学习、强化学习、优化及其他人工智能方向经典算法。 | [技能定义](skills/algo/SKILL.md) |

> **按自己的节奏学习。** `algo` 仅通过 `$algo` 手动启用，用最小例子串联执行流程。只有说“下一步 / next step”才推进主线，其余时间留在当前环节解惑。

## 安装

**1. 克隆仓库**

```sh
git clone https://github.com/changjie-w/SKILLs.git codex-skills
cd codex-skills
```

**2. 选择并安装技能**

以下以 `algo` 为例；安装翻译技能时，将 `skill_name` 改为 `trans`。

```sh
skill_name=algo
skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills_dir"

if [ -e "$skills_dir/$skill_name" ]; then
  printf '目标目录已存在，请先备份并比较：%s\n' "$skills_dir/$skill_name"
else
  cp -R "skills/$skill_name" "$skills_dir/$skill_name"
fi
```

**依赖说明：** `algo` 本身无需额外 Python 依赖；`trans` 的运行环境、辅助命令和测试方法见[使用指南](skills/trans/README.md#安装)。

<details>
<summary>更新与旧版本迁移</summary>

在仓库目录执行 `git pull --ff-only` 获取更新，再比较并同步需要的技能，保留本地修改。

本仓库原名为 `trans`，原来位于根目录的翻译技能已迁入 `skills/trans/`。安装时复制具体技能子目录，不要将整个仓库直接放入个人技能目录下的 `trans/`。

</details>

## 使用示例

**学习算法 · 先看清流程，再按需深入**

```text
$algo 我想学习 PPO，先理解它解决什么问题，以及一轮训练怎样运行。
```

**阅读论文 · 生成英中双语对照 PDF**

```text
用 $trans 翻译 /path/to/paper.pdf，生成全文英中对照 PDF。
```

```text
用 $trans 翻译 Zotero 中的《论文标题》，包含附录。
```

## 目录结构

```text
SKILLs/
├── README.md
└── skills/
    ├── trans/                 # 论文翻译
    │   ├── SKILL.md
    │   ├── README.md
    │   ├── agents/
    │   ├── references/
    │   └── scripts/
    └── algo/                  # 算法学习
        ├── SKILL.md
        └── agents/openai.yaml
```

新增技能时，放入 `skills/<技能名>/`，提供独立的 `SKILL.md` 并更新上方目录；按需添加辅助文件。任务产物、临时环境和个人资料保存在技能目录之外。
