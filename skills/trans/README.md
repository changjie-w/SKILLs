# trans

用于 Codex 的英文论文 PDF 翻译技能：将每个原始页面制作为**左侧英文原页、右侧可检索简体中文**的双语对照 PDF。

支持本地 PDF 与 Zotero 中的论文。默认翻译全文及附录，保留原有分栏、图表和公式的位置；只有用户明确要求时，才将完成的译本作为附件回存到 Zotero 原条目。

## 功能

- 翻译标题、摘要、正文、章节标题、关键词、算法说明、图表标题及附录，不以摘要替代全文。
- 保留作者、机构、出版信息、标识符、版权和许可证；参考文献标题及条目保留原文，纯参考文献页直接复制。
- 每个原页对应一个双语页面，高度不变、宽度加倍，支持混合页面尺寸。
- 中文为可提取、可搜索的文字；复用原始图表、公式和矢量内容。
- 自动检查页数、范围、源文件哈希、原文与保护区域像素、文字提取、字形边界和图注关联；另行逐页进行视觉审查与翻译准确性审查。
- 通过按需加载说明和紧凑数据查看命令减少重复读取，不截断原始文字或舍入坐标。

## 安装

按照[仓库安装说明](../../README.md#安装)安装，将 `skill_name` 设置为 `trans`；应复制本目录，而非整个仓库。目标目录已存在时先备份并比较本地修改。安装后通过 `$trans` 调用。

辅助脚本需要 **Python 3.10+** 和 **PyMuPDF 1.26.5+**。可建立独立环境：

```sh
python3 -m venv ~/.cache/codex-trans/venv
~/.cache/codex-trans/venv/bin/python -m pip install 'PyMuPDF>=1.26.5'
```

默认使用随 PyMuPDF 提供的 CJK 字体，不必另行下载中文字体。Zotero 来源查找还需要安装并配置 Codex 的 Zotero 插件；仅处理本地 PDF 时不需要该插件。

## 使用示例

在 Codex 中发送：

```text
用 $trans 翻译 /path/to/paper.pdf，生成全文英中对照 PDF。
```

```text
用 $trans 翻译 Zotero 中的《论文标题》，包含附录。
```

```text
用 $trans 翻译这篇论文的第 1–3 页，完成检查后回存到 Zotero 原条目。
```

可以指定页码范围、输出目录和交付要求。仅要求翻译不会自动回存 Zotero。回存时保留原始附件和文献信息，检查已有附件的文件哈希以避免重复添加，并读回核验保存结果。

## 工作流程与辅助命令

Codex 负责阅读、翻译、区域划分、排版清单编写与逐页审校；Python 辅助脚本负责提取、排版和文件检查。**脚本本身不会翻译，也不会调用翻译 API 或操作 Zotero。**

以下命令中的 `python` 指已安装依赖的解释器，`<skill>` 指本技能目录。任务文件应保存在技能目录之外。

```sh
# 提取全部页面文字、坐标及图形信息，并生成原文预览
python <skill>/scripts/pdf_regions.py inspect \
  --source paper.pdf --output inventory.json --render-dir source-previews

# 查看页面索引，或完整查看指定页面
python <skill>/scripts/pdf_regions.py view --input inventory.json --kind inventory
python <skill>/scripts/pdf_regions.py view --input inventory.json --kind inventory --pages 1-3

# 使用已准备的译文和区域清单生成双语 PDF
python <skill>/scripts/pdf_regions.py build \
  --source paper.pdf --plan layout.json --output bilingual.pdf \
  --report file-checks.json --render-dir final-previews

# 查看检查概况，必要时展开完整记录
python <skill>/scripts/pdf_regions.py view --input file-checks.json --kind report
python <skill>/scripts/pdf_regions.py view --input file-checks.json --kind report --detail full
```

排版清单的字段、坐标规则和完整契约见 [references/layout.md](references/layout.md)。输出 PDF 和报告路径必须尚未存在；修订时使用新文件名。

每次任务保留三类独立记录：

| 文件 | 用途 |
| --- | --- |
| `file-checks.json` | 文件检查、页面范围、哈希及排版诊断 |
| `visual-review.md` | 逐页检查裁切、重叠、换行、图表与公式 |
| `translation-review.md` | 内容覆盖、术语、公式、数值、引用及翻译准确性 |

## 适用范围与限制

- 常规路径面向具有文字层、白色背景的英文论文。扫描件需要先获得并核验 OCR 文字层；彩色背景、图像上文字等输入需要单独适配。
- 默认保留公式原位。密集行内公式可能需要细分区域或另行验证精确公式排版；本仓库不包含针对某篇论文定制的富文本数学渲染器。
- 区域溢出时只允许在记录的可读字号下限内调整排版。不能通过删减文字、跨栏、移动图表或无限缩小字号强行完成。
- 自动检查不能证明翻译准确，也不能替代逐页视觉审查。未解决的排版或内容问题会阻止将结果标记为完成。
- PDF 链接和交互功能不保证保留。默认不使用图像生成；图片型译文若要求可检索，还需额外添加并验证 OCR 层。
- 真实论文的复杂度不同，回归测试通过不等于保证所有论文都能自动排版成功。

## 目录结构

```text
trans/
├── README.md
├── SKILL.md                 # 技能入口、适用条件与关键约束
├── agents/openai.yaml       # Codex 界面信息及默认提示
├── scripts/
│   ├── pdf_regions.py       # inspect / view / build
│   └── test_pdf_regions.py  # 隔离的合成回归测试
└── references/
    ├── layout.md           # 常规排版操作契约
    ├── exceptions.md       # 环境、字体及特殊输入
    ├── zotero.md           # Zotero 来源定位
    ├── zotero-save.md      # 回存与重复附件防护
    └── maintenance.md      # 维护与测试
```

## 测试

```sh
~/.cache/codex-trans/venv/bin/python scripts/test_pdf_regions.py
```

在本技能目录（仓库中的 `skills/trans/`）执行。现有 20 项测试覆盖混合页面尺寸、参考文献、公式保护、图注关联、旋转、范围和遗漏检查、溢出拒绝、字形边界、紧凑数据查看，以及同条件嵌入比较与保护内容损坏拒绝。测试使用临时合成材料，不访问网络或创建 Zotero 附件。
