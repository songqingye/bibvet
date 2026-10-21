# bibvet

**在审稿人发现之前，先给你的参考文献做个体检。**

`bibvet` 把参考文献逐条拿去和 **Crossref**、**OpenAlex** 的注册数据核对，专抓投稿前最容易漏掉的错误：

- ❌ **失效或编造的 DOI**（两个数据库都查无此条）
- ❌ **年份、卷号、页码写错**（如把 2015 写成 2016）
- ⚠️ **标题、期刊名**与注册记录对不上
- ⚠️ 换了个引用键藏起来的**重复条目**
- ℹ️ **缺 DOI** —— 按标题反查并给出建议 DOI

输入不挑格式：可以是 **`.bib` 文件**，也可以是直接从 Word/PDF 里粘出来的**纯文本参考文献列表**，包括国标 GB/T 7714 格式（`[1] 作者. 题名[J]. 刊名, 年, 卷(期): 页码.`）。

零第三方依赖，只用 Python 标准库。English version: [README.md](README.md).

## 安装

```bash
pip install bibvet        # 发布到 PyPI 后
# 或克隆仓库后本地安装：
pip install .
```

需要 Python 3.9+，无需任何 API 密钥。

## 用法

```bash
bibvet check references.bib
bibvet check references.txt --report report.md --bib-out fixed.bib
bibvet check refs.bib --offline     # 只查重复和格式，不联网
```

发现 error 时退出码为 1，可以直接挂到投稿前脚本或 CI 里。

### 示例

对 [examples/example.bib](examples/example.bib)（故意埋了错年、错卷、假 DOI、重复条目和一条缺 DOI）：

```text
[lecun2015deep] ✅ ok  Deep learning
[lecun2015wrongyear] ❌ error
    ⚠️ year-mismatch: yours 2016, registry 2015
    ⚠️ volume-mismatch: yours 522, registry 521
    ❌ duplicate: 与 lecun2015deep 重复（同一 DOI）
[fake2020] ❌ error
    ❌ doi-not-found: 10.1038/nature99999 在 Crossref 和 OpenAlex 均无记录
[hochreiter1997lstm] ✅ ok
    ℹ️ doi-suggested: 建议 DOI: 10.1162/neco.1997.9.8.1735
```

加 `--bib-out fixed.bib` 会输出一份**修正版 .bib**：错年、错卷按注册数据改对，缺的 DOI、出版社自动补上，引用键保持不变。纯文本示例见 [examples/references.txt](examples/references.txt)（国标格式，故意把 LSTM 的年份写成 1998，能被抓出并建议正确 DOI）。生成的报告示例在 [demo/](demo/) 目录。

## 匹配为什么这么谨慎

只凭标题相同绝不下结论——不同文献会重名（真有一本 2021 年百科全书的章节就叫 "Short-Term/Long-Term Memory"）。bibvet 给出建议 DOI 前，要求**年份 / 第一作者 / 期刊**三项里至少两项对得上，且最多容忍一项不一致（不一致的那项随后会被作为疑似错误报出来）。凑不齐佐证的条目标记为 `❔ unverified` 并列出最接近的候选，宁可说“没查准”，也不给自信的错误答案。

已知局限：少数会议/老文献在注册库里覆盖差（如早期 NeurIPS），这类条目会返回 unverified，不会被误判为 ok。

## 选项

| 参数 | 作用 |
|---|---|
| `--report PATH` | Markdown 核查报告 |
| `--json PATH` | JSON 格式报告 |
| `--bib-out PATH` | 输出修正版 .bib |
| `--email ADDR` | Crossref 礼貌池联系邮箱（可选，可能更快） |
| `--offline` | 离线模式，只查重复与格式 |
| `--quiet` | 不打印终端输出 |

## 路线图

- [ ] Zotero 文献库直接核查
- [ ] GB/T 7714、APA 格式 lint（标点、排序）
- [ ] arXiv 编号核查
- [ ] 拖拽式网页界面

欢迎 PR，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT © 2026 Song Qingye
