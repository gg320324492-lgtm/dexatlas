import { useRef, useState, type DragEvent, type ReactNode } from "react";
import "./DragDropUploader.css";

export interface DragDropUploaderProps {
  /** 接受的扩展名，如 [".apk", ".apks"] */
  accept?: string[];
  /** 单文件大小上限（MB），超限拒绝并提示 */
  maxSizeMB?: number;
  /** 选择/拖入文件（已通过扩展名与大小校验） */
  onFileSelected: (file: File) => void;
  /** 校验失败提示 */
  onRejected?: (reason: string) => void;
  title?: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}

/**
 * 拖拽上传器：首屏“拖入 APK”入口。
 * 仅做前端校验（扩展名 + 大小），不发起上传请求。
 */
export function DragDropUploader({
  accept = [".apk"],
  maxSizeMB = 512,
  onFileSelected,
  onRejected,
  title = "拖入 APK 文件",
  description,
  disabled = false,
}: DragDropUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const validateAndEmit = (file: File) => {
    const lower = file.name.toLowerCase();
    if (accept.length > 0 && !accept.some((ext) => lower.endsWith(ext.toLowerCase()))) {
      onRejected?.(`文件类型不受支持：${file.name}（期望 ${accept.join(" / ")}）`);
      return;
    }
    if (file.size > maxSizeMB * 1024 * 1024) {
      onRejected?.(`文件过大：${file.name}（上限 ${maxSizeMB} MB）`);
      return;
    }
    setFileName(file.name);
    onFileSelected(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndEmit(file);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  };

  return (
    <div
      className={["da-uploader", dragOver ? "da-uploader--over" : "", disabled ? "da-uploader--disabled" : ""]
        .filter(Boolean)
        .join(" ")}
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={() => setDragOver(false)}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-label={typeof title === "string" ? title : "上传文件"}
      aria-disabled={disabled}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (!disabled) inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept.join(",")}
        className="da-uploader__input"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) validateAndEmit(file);
          e.target.value = "";
        }}
      />
      <div className="da-uploader__icon" aria-hidden="true">
        ⇪
      </div>
      <div className="da-uploader__title">{title}</div>
      <div className="da-uploader__desc">
        {description ?? `支持 ${accept.join(" / ")}，单个文件不超过 ${maxSizeMB} MB`}
      </div>
      {fileName ? <div className="da-uploader__file">已选择：{fileName}</div> : null}
    </div>
  );
}
