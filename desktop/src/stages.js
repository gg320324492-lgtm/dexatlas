/**
 * 分析页的阶段映射 —— 纯函数，无 React 依赖，可被直接执行。
 *
 * 【为什么是 .js 而不是 .ts】
 * 这个模块是**无依赖的纯 ESM**：不改一行就能被 Node 直接执行、被 vitest
 * 直接 import、被浏览器直接加载——桌面端的三种用法读的是同一份文件，不必
 * 先构建一步。类型并没有因此丢失：desktop/tsconfig.json 打开了
 * allowJs + checkJs，tsc 会按 JSDoc 里的类型逐行检查本文件，桌面端
 * npm run build 仍然是全量类型检查（tsc --noEmit && vite build）。
 * 它的单元测试在 desktop/src/stages.test.ts（vitest），由 CI 的 desktop
 * job 跑；阶段映射的回归从此有了自己的拦截网，不必再靠别的语言读源码。
 *
 * 【映射规则】（优先级从高到低）
 * 1. 有阶段事件（Phase 5 W2 的 stages 端点）→ 按事件置 done / running；
 *    run 已终止却停在某阶段的格子标 error；completeness = "partial" 时，
 *    按 errors 点名的工具在已完成格子上标注「部分」（skipped 态）。
 * 2. 否则按 run.status 粗粒度映射（旧后端写入的 run 没有阶段事件）：
 *    pending → 全部待处理；running → 采集完成、解析进行中；
 *    completed → 五阶段全部完成；failed / cancelled → 采集完成、解析标失败。
 * 3. 两者皆无时由调用方回退前端时间模拟（deriveStageStates）。
 *
 * 【「证据」格是推断值】
 * 后端的五个阶段里没有「证据」：inspect → 采集、parse-apktool 与
 * decompile-jadx → 解析、index-androguard → 索引、publish → 报告。
 * 证据由 pipeline 在 publish 之前产出（src/dexatlas/core/pipeline.py:345
 * 建证据，:383 才发布），所以「证据」格的状态只能推断，页面角标必须
 * 如实说明这一点（见 deriveStageBadge）。
 */

/**
 * @typedef {import("./types").StageId} StageId
 * @typedef {import("./types").StageInfo} StageInfo
 * @typedef {import("./types").StageState} StageState
 * @typedef {import("./api/types").RunStageEvent} StageEvent
 */

/**
 * 映射只需要 run 上的这几个字段；errors 是历史形状里 run 自带的可选字段。
 * @typedef {Object} RunFacts
 * @property {string} status
 * @property {string} completeness
 * @property {unknown} [errors]
 */

/**
 * @typedef {Object} StageStates
 * @property {Record<string, StageState>} states
 * @property {Record<string, string>} partialLabels
 */

/** 页面五阶段格子（左侧阶段进度）。 @type {StageInfo[]} */
export const STAGES = [
  { id: "collect", label: "采集", description: "读取 APK 结构、manifest 与签名信息" },
  { id: "parse", label: "解析", description: "Apktool 反编译资源与 Smali，JADX 还原 Java 源码" },
  { id: "index", label: "索引", description: "Androguard 建立类/方法/字段符号索引" },
  { id: "evidence", label: "证据", description: "抽取权限、组件、字符串与敏感调用点" },
  { id: "report", label: "报告", description: "汇总为可复核的 Markdown / JSON 报告" },
];

/** 格子的先后顺序（推断用）。 @type {StageId[]} */
export const SLOT_ORDER = ["collect", "parse", "index", "evidence", "report"];

/** 后端 pipeline 阶段 → 页面五阶段格子。 @type {Record<string, StageId>} */
export const STAGE_TO_SLOT = {
  inspect: "collect",
  "parse-apktool": "parse",
  "index-androguard": "index",
  "decompile-jadx": "parse",
  publish: "report",
};

/**
 * 「证据」格的说明：后端没有这个阶段事件，状态是推断出来的。
 * 页面把这句话挂在该格上，不让读者以为它是后端报出来的。
 */
export const EVIDENCE_SLOT_NOTE = "「证据」格在后端没有对应的阶段事件，状态由已完成的阶段推断得出";

/**
 * 「解析」格合并了两个后端阶段（parse-apktool 与 decompile-jadx）。
 * 页面角标要如实说明，否则读者会以为后端只反编译了一份。
 */
export const PARSE_SLOT_NOTE = "「解析」格合并了后端的 parse-apktool 与 decompile-jadx 两个阶段";

/**
 * 阶段推进的角标：如实说明数据来源。
 *
 * @param {"stages" | "run-status" | "simulation"} source
 * @param {boolean} [stagesUnavailable] stages 端点不可用（404 / 网络）
 * @returns {{ text: string, title: string }}
 */
export function deriveStageBadge(source, stagesUnavailable = false) {
  if (source === "stages") {
    return {
      text: "阶段推进：后端真实阶段事件",
      title: `阶段状态读自后端 stages 端点的真实阶段事件（pipeline 推进点）。${PARSE_SLOT_NOTE}；${EVIDENCE_SLOT_NOTE}。`,
    };
  }
  if (source === "run-status") {
    return {
      text: `阶段推进：后端 run 状态 + 前端粒度模拟${stagesUnavailable ? "（stages 端点不可用）" : ""}`,
      title: `该 run 无阶段级数据（旧后端写入），状态由 run.status 映射，粒度由前端推断；${PARSE_SLOT_NOTE}；${EVIDENCE_SLOT_NOTE}。`,
    };
  }
  return {
    text: "阶段推进为前端模拟",
    title: `后端 runs 不可用，阶段推进由前端按时间模拟，完成/失败时与真实状态对齐；${PARSE_SLOT_NOTE}；${EVIDENCE_SLOT_NOTE}。`,
  };
}

/**
 * 阶段推进模拟：仅在后端连 run 状态都拿不到时兜底（按时间近似推进）。
 * 返回每个格子的状态。
 *
 * @param {number} progress 已完成的格数（0..STAGES.length）
 * @param {string | null} status
 * @returns {Record<string, StageState>}
 */
export function deriveStageStates(progress, status) {
  /** @type {Record<string, StageState>} */
  const states = {};
  STAGES.forEach((stage, i) => {
    if (status === "completed") {
      states[stage.id] = "done";
    } else if (status === "failed") {
      states[stage.id] = i < progress ? "done" : i === progress ? "error" : "pending";
    } else {
      states[stage.id] = i < progress ? "done" : i === progress ? "running" : "pending";
    }
  });
  return states;
}

/**
 * 阶段映射：优先用 stages 端点的真实阶段事件（Phase 5 W2），按事件推进置
 * done/running；run 未结束且 publish 未完成时，证据格按最后已完成的阶段
 * 推断。端点无 stages（旧后端写入的 run）回退到 run.status 的粗粒度
 * 映射；两者皆无时由调用方回退时间模拟。
 *
 * @param {RunFacts | null} run
 * @param {StageEvent[] | null} runStages
 * @returns {StageStates}
 */
export function deriveStagesFromRun(run, runStages) {
  /** @type {Record<string, StageState>} */
  const states = {};
  /** @type {Record<string, string>} */
  const partialLabels = {};

  if (!run) {
    STAGES.forEach((s) => (states[s.id] = "pending"));
    return { states, partialLabels };
  }

  const events = runStages ?? [];
  if (events.length > 0) {
    STAGES.forEach((s) => (states[s.id] = "pending"));
    /** @type {StageId | null} */
    let lastDoneSlot = null;
    // publish 有没有被走到：证据在 publish 之前产出（pipeline.py:345 建证据，
    // :383 才发布），所以只要 publish 到了，证据就已经存在。
    let publishReached = false;
    for (const event of events) {
      const slot = STAGE_TO_SLOT[event.stage];
      if (!slot) continue;
      if (slot === "report") publishReached = true;
      if (event.finished_at) {
        states[slot] = "done";
        lastDoneSlot = slot;
      } else if (run.status === "running" || run.status === "pending") {
        states[slot] = "running";
      } else {
        // run 已终止（failed/cancelled）却停在某个阶段：该格标失败
        states[slot] = "error";
      }
    }
    // 证据格没有自己的后端事件（它由各阶段的产出汇成），状态只能推断：
    // - publish 到了 → 证据已产出（done）。完成态必须落在这里：后端最后一个
    //   阶段 publish 落在「报告」格，若在这里把证据判成"没到"，一个已经产出
    //   证据的完成 run 会显示「证据 · 待处理」，和页面顶部的「已完成」、
    //   横幅的「N 条证据」自相矛盾（复测报告 §P1，9/9 复现）。
    // - run 已终止却还没进 publish → 证据从未产出，保持 pending（也不能停在
    //   「进行中」：run 都结束了）。
    // - run 还在跑 → 按最后一个已完成的阶段推断（它之后的格子依次推进）。
    if (states.evidence === "pending") {
      if (publishReached) {
        states.evidence = "done";
      } else if (run.status === "running" || run.status === "pending") {
        if (lastDoneSlot && lastDoneSlot !== "report") {
          const lastIdx = SLOT_ORDER.indexOf(lastDoneSlot);
          const evidenceIdx = SLOT_ORDER.indexOf("evidence");
          if (evidenceIdx > lastIdx) {
            states.evidence = lastIdx >= evidenceIdx - 1 ? "running" : "pending";
          }
        }
      }
    }
    applyPartial(run, states, partialLabels);
    return { states, partialLabels };
  }

  // ---- 回退：旧 run（无阶段事件）按状态粗粒度映射 ----
  if (run.status === "pending") {
    // run 还没开始：五个格子都还没开始（RunStatus.PENDING 是真实存在的状态）
    STAGES.forEach((s) => (states[s.id] = "pending"));
    return { states, partialLabels };
  }

  if (run.status === "running") {
    // 保守映射：采集已完成，解析进行中，其余未开始
    states.collect = "done";
    states.parse = "running";
    states.index = "pending";
    states.evidence = "pending";
    states.report = "pending";
    return { states, partialLabels };
  }

  if (run.status === "completed") {
    STAGES.forEach((s) => (states[s.id] = "done"));
    applyPartial(run, states, partialLabels);
    return { states, partialLabels };
  }

  // failed：run 已终止且未发布；把"解析"格标失败（首个非采集阶段）
  states.collect = "done";
  states.parse = "error";
  states.index = "pending";
  states.evidence = "pending";
  states.report = "pending";
  return { states, partialLabels };
}

/**
 * completeness = "partial" 时，按 errors 点名的工具把已完成的格子标成
 * 「部分」（skipped 态）；errors 形如 "jadx: ..." / "apktool: ..."。
 *
 * @param {RunFacts} run
 * @param {Record<string, StageState>} states
 * @param {Record<string, string>} partialLabels
 */
function applyPartial(run, states, partialLabels) {
  if (run.completeness !== "partial") return;
  const errors = readCompletenessErrors(run);
  const affected = new Set();
  for (const msg of errors) {
    const tool = msg.split(":")[0]?.trim().toLowerCase() ?? "";
    if (tool.includes("jadx") || tool.includes("apktool")) affected.add("parse");
    if (tool.includes("androguard")) affected.add("index");
    if (tool.includes("evidence")) affected.add("evidence");
    if (tool.includes("report")) affected.add("report");
  }
  if (affected.size === 0) affected.add("report");
  affected.forEach((id) => {
    if (states[id] === "done") {
      states[id] = "skipped"; // 复用 partial 徽章语义
      partialLabels[id] = "部分";
    }
  });
}

/**
 * run.completeness.errors 的两种历史形状 → 字符串数组。
 *
 * @param {RunFacts} run
 * @returns {string[]}
 */
export function readCompletenessErrors(run) {
  const raw = run.errors;
  if (!Array.isArray(raw)) return [];
  return raw.map((e) =>
    typeof e === "string" ? e : `${e && typeof e === "object" && "tool" in e ? e.tool : ""}: ${e && typeof e === "object" && "message" in e ? e.message : ""}`,
  );
}
