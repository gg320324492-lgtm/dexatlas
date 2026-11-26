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
 * 3. 没有 run 数据时五格全部「待处理」：状态未知就是未知，这里不按时间
 *    推测进度（前端时间模拟已在 Phase 5 收尾删除）。
 *
 * 【「证据」格是推断值】
 * 后端的五个阶段里没有「证据」：inspect → 采集、parse-apktool 与
 * decompile-jadx → 解析、index-androguard → 索引、publish → 报告。
 * 证据由 pipeline 在 publish 之前产出（src/dexatlas/core/pipeline.py:345
 * 建证据，:383 才发布），所以「证据」格的状态只能推断，页面角标必须
 * 如实说明这一点（见 deriveStageBadge）。
 *
 * 【什么算终态、什么时候停止轮询】
 * 后端有两套状态字段：「一个项目怎么样了」（project.status）与「这一轮
 * 分析怎么了」（run.status）。本模块给出唯一一份终态口径
 * （isTerminalStatus），并给出「进了终态就停」的轮询规则
 * （pollUntilTerminal）。规则放在这里，是因为它必须能在没有 DOM 的地方
 * 被直接执行和测试（CI 的 desktop job 跑 vitest，环境是 node）；页面只
 * 负责把后端的事实画出来，不自己决定「什么时候算结束」。
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
 * 【两件事要分开说】
 * - 后端给的**事实**：阶段事件（stages 端点）或 run 的状态字段；
 * - 前端做的**映射**：五个格子分别对应哪个后端阶段、哪一格算「推进到位」。
 * 角标只写一句短话，所以正文里点明后半句是前端的映射，展开说明放在
 * title（悬停可见）里；两处都不能含糊，否则读者会以为格子上的状态是
 * 后端直接报出来的。
 *
 * @param {"stages" | "run-status"} source
 * @param {boolean} [stagesUnavailable] stages 端点不可用（404 / 网络）
 * @returns {{ text: string, title: string }}
 */
export function deriveStageBadge(source, stagesUnavailable = false) {
  if (source === "stages") {
    return {
      text: "阶段推进：后端阶段事件 + 前端映射",
      title: `阶段事件读自后端 stages 端点（pipeline 推进点，后端事实）；五格与后端阶段的对应关系、哪一格算「推进到位」，由前端的映射与推断决定（desktop/src/stages.js）。${PARSE_SLOT_NOTE}；${EVIDENCE_SLOT_NOTE}。`,
    };
  }
  return {
    text: `阶段推进：后端 run 状态 + 前端映射${stagesUnavailable ? "（stages 端点不可用）" : ""}`,
    title: `该 run 无阶段级数据（旧后端写入），格子的状态由前端按 run.status 静态映射，不随时间推进；${PARSE_SLOT_NOTE}；${EVIDENCE_SLOT_NOTE}。`,
  };
}

/**
 * 终态集合：completed / failed / cancelled。
 *
 * 【两个状态字段，一套口径】
 * - run.status（src/dexatlas/core/runs.py:52 RunStatus）：pending / running /
 *   completed / failed / cancelled；
 * - project.status（src/dexatlas/core/models.py:748 ProjectStatus）：pending /
 *   running / completed / failed —— 没有 cancelled：被取消的分析把项目留在
 *   failed（src/dexatlas/core/pipeline.py:490 _record_cancellation「Leave the
 *   project failed, and say that it was cancelled」）。
 * 各处轮询（项目状态、runs 列表、阶段事件）因此共用这一个判定：项目落在
 * completed/failed 时停，run 落在 completed/failed/cancelled 时停。
 *
 * @type {readonly string[]}
 */
export const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

/**
 * 这个状态是不是终态（不会再变了）。
 *
 * 未知状态（null、空串、后端将来新增的状态）一律算「不是终态」：宁可多问
 * 一次后端，也不要在没读到事实时假装已经结束——那会让页面停在半路而没人
 * 知道它在等什么。
 *
 * @param {string | null | undefined} status 后端返回的状态字段值
 * @returns {boolean}
 */
export function isTerminalStatus(status) {
  return typeof status === "string" && TERMINAL_STATUSES.includes(status);
}

/**
 * 定时器来源：浏览器里是 window 的那套，测试里注入假的（node 环境没有
 * window，而且真定时器会让测试等真实时间）。
 *
 * @typedef {Object} PollScheduler
 * @property {(fn: () => void, ms: number) => number} setInterval
 * @property {(handle: number) => void} clearInterval
 */

/** 默认的定时器来源：全局 setInterval（浏览器与 node 都有）。 @type {PollScheduler} */
const DEFAULT_SCHEDULER = {
  setInterval: (fn, ms) => globalThis.setInterval(fn, ms),
  clearInterval: (handle) => globalThis.clearInterval(handle),
};

/**
 * 轮询一个后端事实源，进了终态就停。
 *
 * 【终态判定依据】isTerminal()，由调用方给出，判据只能是后端返回的状态
 * 字段（项目的 project.status、run 的 run.status）——不是时间，也不是前端
 * 的猜测。终态集合见 isTerminalStatus；页面上的各处轮询共用它。
 *
 * 【为什么停】项目已经跑完（或失败、取消）之后，定时器还在转就等于每两秒
 * 问一次后端一个不会变的答案：白花请求，也让「还在跑」的错觉留在页面上。
 * 判定为终态后立刻清掉定时器；组件卸载时调用 stop() 也能清。
 *
 * @param {Object} options
 * @param {() => Promise<void> | void} options.poll 一次轮询；错误由页面层自己如实记录
 * @param {() => boolean} options.isTerminal 终态判定
 * @param {number} options.intervalMs 轮询间隔（毫秒）
 * @param {PollScheduler} [options.scheduler] 定时器来源（默认全局；测试注入假的）
 * @returns {{ stop: () => void }} stop() 手动停（组件卸载时调用）
 */
export function pollUntilTerminal({
  poll,
  isTerminal,
  intervalMs,
  scheduler = DEFAULT_SCHEDULER,
}) {
  let stopped = false;
  /** @type {number | undefined} */
  let handle;

  const stop = () => {
    stopped = true;
    if (handle !== undefined) {
      scheduler.clearInterval(handle);
      handle = undefined;
    }
  };

  const tick = async () => {
    if (stopped) return;
    try {
      await poll();
    } catch {
      // poll 的错误由页面层如实记录并继续轮询；这里只是不让一次意外的抛出
      // 变成未处理的拒绝，也不因此判定终态。
      return;
    }
    if (stopped) return;
    // 终态 → 停掉定时器，不再发下一次请求。
    if (isTerminal()) stop();
  };

  // 先挂定时器再跑第一次：这样第一次 poll 结束时 handle 一定已经就位，
  // stop() 才不会漏掉清理（漏了就等于停不下来）。
  handle = scheduler.setInterval(() => void tick(), intervalMs);
  void tick();
  return { stop };
}

/**
 * 阶段映射：优先用 stages 端点的真实阶段事件（Phase 5 W2），按事件推进置
 * done/running；run 未结束且 publish 未完成时，证据格按最后已完成的阶段
 * 推断。端点无 stages（旧后端写入的 run）回退到 run.status 的粗粒度
 * 映射；没有 run 数据时五格全部待处理（状态未知，不做时间推测）。
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
    // 没有 run 数据：五个格子的状态未知，全部如实显示「待处理」。
    // 这里不按时间推进——拿不到后端事实时不编造一个看起来像事实的进度。
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

/**
 * 后端状态区的映射 —— 纯函数，无 React 依赖。
 *
 * 【三种状态，不是两种】
 * `tool_versions` 的**键**说明这一轮有没有带上这个后端，值说明它的版本。
 * 值可能是 `null`，那有两种意思：版本还没探测出来（分析刚开始，探测还在
 * 跑），或者它压根没装上。这两者必须分开说——把「还没探测」说成「未安装」
 * 是在对用户说假话，而那正是 Phase 5 收尾时在打包 exe 上实测到的现象。
 *
 * @typedef {import("./types").BackendState} BackendState
 * @typedef {import("./types").BackendStatus} BackendStatus
 */

/** 页面右栏的三个后端，顺序即页面上的顺序。 @type {Array<{name: string, key: string}>} */
export const BACKEND_KEYS = [
  { name: "JADX", key: "jadx" },
  { name: "Apktool", key: "apktool" },
  { name: "Androguard", key: "androguard" },
];

/**
 * 从最近一轮 run 的 tool_versions 推断三个后端的状态。
 *
 * @param {{runs?: Array<{tool_versions?: Record<string, string | null>}>} | null} project
 * @returns {BackendStatus[]}
 */
export function deriveBackends(project) {
  const latest = project && project.runs ? project.runs[0] : undefined;
  const versions = (latest && latest.tool_versions) || {};
  const hasRun = Boolean(latest);
  return BACKEND_KEYS.map(({ name, key }) => {
    if (!hasRun) {
      return { name, state: "queued", detail: "等待分析轮次数据…" };
    }
    if (!(key in versions)) {
      // 这一轮的记录里没有它：它没有参与这次分析。
      return { name, state: "error", detail: "未安装或未配置，未参与本次分析" };
    }
    const version = versions[key];
    if (version) {
      return { name, state: "done", detail: `v${version} · 参与本次分析` };
    }
    // 键在、值为空：后端参与了这一轮，版本还没探测出来。
    return { name, state: "running", detail: "参与本次分析 · 版本探测中" };
  });
}
