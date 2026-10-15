# Codex Skills

个人 Codex 技能集合。仓库地址保留为 `changjie-w/trans`，各技能独立保存在 `skills/` 下，后续可继续添加其他技能。

## 技能目录

| 技能 | 用途 | 入口与说明 |
| --- | --- | --- |
| `trans` | 将英文论文 PDF 制作为左英文、右可检索简体中文的逐页双语 PDF，支持本地文件与 Zotero | [技能入口](skills/trans/SKILL.md) · [使用说明与依赖](skills/trans/README.md) |
| `algo` | 学习机器学习、强化学习、优化及其他人工智能方向经典算法，支持论文、教材、课程材料、代码和算法名称等入口 | [技能入口](skills/algo/SKILL.md) |

`algo` 仅通过 `$algo` 手动启用：系统学习时先概述、校准目标并确认主线，只有用户说“下一步 / next step”才推进；独立问题直接解惑。

## 目录结构

```text
skills/
├── trans/
│   ├── SKILL.md
│   ├── README.md
│   ├── agents/
│   ├── references/
│   └── scripts/
└── algo/
    ├── SKILL.md
    └── agents/openai.yaml
```

## 安装

克隆仓库后，将需要的技能子目录复制到 Codex 的个人技能目录。以下以 `algo` 为例，安装 `trans` 时将 `skill_name` 改为 `trans`：

```sh
git clone https://github.com/changjie-w/trans.git codex-skills
cd codex-skills
skill_name=algo
skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills_dir"
if [ -e "$skills_dir/$skill_name" ]; then
  printf '目标目录已存在，请先备份并比较：%s\n' "$skills_dir/$skill_name"
else
  cp -R "skills/$skill_name" "$skills_dir/$skill_name"
fi
```

旧版仓库根目录中的 `trans` 文件已迁入 `skills/trans/`。安装时选择具体技能子目录，不要把整个仓库直接作为 `trans` 安装。更新仓库后，先比较本地修改，再同步所需技能。

`algo` 本身无需额外 Python 依赖。`trans` 的运行依赖、辅助命令和测试方法见其[使用说明](skills/trans/README.md)。

## 调用示例

```text
$algo 我想学习 PPO，先理解整体工程流程。
```

```text
用 $trans 翻译 /path/to/paper.pdf，生成全文英中对照 PDF。
```

## 添加其他技能

在 `skills/<技能名>/` 中放置独立的 `SKILL.md`，按需添加 `agents/`、`scripts/` 或 `references/`，并更新上方技能目录。任务产物、临时环境和个人资料不放入技能目录。
