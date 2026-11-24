import { useState, type ReactNode } from "react";
import "./SourcePreview.css";

export interface SourcePreviewLanguageConfig {
  /** 行内高亮关键词（简单词法，不引语法高亮库） */
  keywords?: string[];
  comments?: boolean;
}

export interface SourcePreviewProps {
  /** 源码/Smali 文本 */
  code: string;
  /** 文件路径或类名（展示在头部） */
  path?: string;
  language?: string;
  /** 起始行号（对应真实文件行，便于证据引用） */
  startLine?: number;
  /** 高亮行号（1-based，相对文件） */
  highlightLines?: number[];
  actions?: ReactNode;
  /** 折叠长文件：默认最多显示 200 行 */
  maxLines?: number;
}

/**
 * 源码预览：展示反编译 Java / Smali / Manifest 片段。
 * 带行号与目标行高亮，是“结论回跳来源”的展示端。
 */
export function SourcePreview({
  code,
  path,
  language = "java",
  startLine = 1,
  highlightLines = [],
  actions,
  maxLines = 200,
}: SourcePreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const allLines = code.split("\n");
  const visible = expanded ? allLines : allLines.slice(0, maxLines);
  const hidden = allLines.length - visible.length;
  const highlight = new Set(highlightLines);

  return (
    <figure className="da-srcpreview">
      <figcaption className="da-srcpreview__header">
        <div className="da-srcpreview__meta">
          <span className="da-srcpreview__lang">{language}</span>
          {path ? <span className="da-srcpreview__path">{path}</span> : null}
        </div>
        <div className="da-srcpreview__actions">{actions}</div>
      </figcaption>
      <div className="da-srcpreview__code" role="figure" aria-label={path ? `源码预览 ${path}` : "源码预览"}>
        <table className="da-srcpreview__table">
          <tbody>
            {visible.map((line, i) => {
              const lineNo = startLine + i;
              const isHl = highlight.has(lineNo);
              return (
                <tr key={i} className={isHl ? "da-srcpreview__row--highlight" : undefined}>
                  <td className="da-srcpreview__lineno">{lineNo}</td>
                  <td className="da-srcpreview__line">
                    <code>{line || " "}</code>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {hidden > 0 ? (
          <button type="button" className="da-srcpreview__more" onClick={() => setExpanded(true)}>
            展开剩余 {hidden} 行
          </button>
        ) : null}
      </div>
    </figure>
  );
}
