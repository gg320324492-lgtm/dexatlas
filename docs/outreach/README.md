# `docs/outreach/` 外发材料

> **内部说明——不对外、不作附件、不随提案发送。** 这一页是给自己看的：它说
> 哪一份发出去、哪一份不发，以及发之前要做哪一步。对外的只有下面「发出去的
> 三份」本身。

## 哪一份发出去

| 文件 | 发出去吗 | 说明 |
|---|---|---|
| `cover-letter-templates.md` | ✅ 发（信） | 两封信的模板。`{{...}}` 是**发送前要替换**的业务占位符。 |
| `project-brief.md` | ✅ 发（作品集简介） | 一页项目简介。 |
| `scope-backend-automation.md` | ✅ 发（服务范围） | 一个方向的服务范围声明。 |
| `scope-ai-mcp.md` | ✅ 发（服务范围，另一方向） | 不写测试数与覆盖率，所以**没有**标记，也**不在**导出列表里。 |
| `scope-ai-mcp-compact.md` | ✅ 发（压缩稿） | 同上，压缩版。 |
| `publish-review.md` | ❌ **不发** | 内部核对记录：核对基准、提交号、本机路径、编辑决定。它自己开头就写明了这一点。 |
| `c12-field-check-template.md` | ❌ **不发** | 渠道字段核对表（模板 + 备料结论）。 |

## 发之前要做的一步：导出

**仓库里的文件是「源」，不是「粘贴用的成品」。**

三份带数字的材料里，测试数与覆盖率写在 `fig:` 标记之间，由
`scripts/refresh-report-figures.py` 从真实测量写入——**不用再手抄**。标记是
HTML 注释，粘进表单是可见的乱码，所以发出去的是渲染出来的纯文本：

```bash
uv run --no-sync python scripts/export-outreach.py
```

然后从 `.scratch/outreach-export/` 里取文件。**不要粘仓库里的源。**

导出件不进版本库：它的内容由当前测量决定，而测量每次都不同。

**这一页（以及别处）的说明不进外发件。** 外发件是要发给客户的，里面放
「先跑 `uv run --no-sync python scripts/export-outreach.py`」这种仓库内的操作
说明，一是泄露仓库内部做法，二是**占字符**——`scope-backend-automation.md` 全文
的 5,000 字符门限只剩 59 字符余量，加一段说明就超限。说明放在这里，不放在
外发件里。

## 三道门禁在看着

| 门禁 | 看什么 |
|---|---|
| `scripts/check-version-claims.py` | 外发材料里**标记的值**与执行报告一致（精确比较，无容差）；标记外的数照旧核对 |
| `scripts/export-outreach.py --check` | 每份材料都渲染得出来，且导出件里**不残留标记** |
| `scripts/refresh-report-figures.py --check` | 材料里的标记就是当前测量写的那些数 |

**这三道里任何一道红，外发材料就不该发。**

## 字符数

字段长度（标题 ≤60、简介 ≤5,000、提案正文 ≤2,500）是**平台门限**，不是测量数。
实测值与复算方法在 `publish-review.md` §5——**量的是导出件，不是源**。

## 为什么这么定

设计推理、逐条取舍（A / B / C）与代价写在
[`../reports/outreach-figures.md`](../reports/outreach-figures.md)。
