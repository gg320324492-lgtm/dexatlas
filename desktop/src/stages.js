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
 *    completed → 五格全部完成；failed / cancelled → 采集完成、解析标失败。
 * 3. 没有 run 数据时五格全部「待处理」：状态未知就是未知，这里不按时间
 *    推测进度（前端时间模拟已在 Phase 5 收尾删除）。
 *
 * 【格子与后端阶段一一对应】
 * 后端的五个推进点各占一格：inspect → 采集、parse-apktool → 解析、
 * index-androguard → 索引、decompile-jadx → 反编译、publish → 报告。
 * 所以格上的状态**就是后端报的事实**，没有推断，也没有一格对好几个阶段。
 *
 * 以前不是这样：「解析」格合并了 parse-apktool 与 decompile-jadx 两个阶
 * 段，「证据」格在后端根本没有对应阶段（证据由 pipeline 在 publish 之前产
 * 出，src/dexatlas/core/pipeline.py:345 建证据、:383 才发布），状态只能推
 * 断。两处都靠角标解释，一一对应之后就不必解释了（见 deriveStageBadge）。
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
  { id: "parse-apktool", label: "解析", description: "Apktool 反编译资源与 Smali" },
  { id: "index", label: "索引", description: "Androguard 建立类/方法/字段符号索引" },
  { id: "decompile-jadx", label: "反编译", description: "JADX 还原 Java 源码" },
  { id: "report", label: "报告", description: "汇总为可复核的 Markdown / JSON 报告" },
];

/** 格子的先后顺序（推断用）。 @type {StageId[]} */
export const SLOT_ORDER = ["collect", "parse-apktool", "index", "decompile-jadx", "report"];

/**
 * 后端 pipeline 阶段 → 页面格子。**一一对应**：后端的五个推进点各占一格。
 *
 * 以前这里是五格对一个五阶段的管线，而两处对不上：「解析」格合并了
 * parse-apktool 与 decompile-jadx 两个阶段，「证据」格在后端根本没有对应
 * 阶段、状态是推断出来的。现在每格说一件后端真做过的事，一一对应。
 *
 * @type {Record<string, StageId>}
 */
export const STAGE_TO_SLOT = {
  inspect: "collect",
  "parse-apktool": "parse-apktool",
  "index-androguard": "index",
  "decompile-jadx": "decompile-jadx",
  publish: "report",
};

/**
 * 阶段推进的角标：如实说明数据来源。
 *
 * 【两件事要分开说】
 * - 后端给的**事实**：阶段事件（stages 端点）或 run 的状态字段；
 * - 前端做的**映射**：哪一格算「推进到位」。
 * 角标只写一句短话，所以正文里点明后半句是前端的映射，展开说明放在
 * title（悬停可见）里；两处都不能含糊，否则读者会以为格子上的状态是
 * 后端直接报出来的。
 *
 * 格子与后端阶段**一一对应**：inspect / parse-apktool / index-androguard /
 * decompile-jadx / publish 各占一格，所以这里不再需要解释哪一格对应哪
 * 几个阶段——以前要解释，是因为「解析」格合并了两个阶段、「证据」格在后
 * 端没有对应阶段而状态是推断的。那一格已经拆掉了。
 *
 * @param {"stages" | "run-status"} source
 * @param {boolean} [stagesUnavailable] stages 端点不可用（404 / 网络）
 * @returns {{ text: string, title: string }}
 */
export function deriveStageBadge(source, stagesUnavailable = false) {
  if (source === "stages") {
    return {
      text: "阶段推进：后端阶段事件 + 前端映射",
      title: `阶段事件读自后端 stages 端点（pipeline 推进点，后端事实）；五格与后端的五个推进点一一对应，哪一格算「推进到位」由前端的映射决定（desktop/src/stages.js）。`,
    };
  }
  return {
    text: `阶段推进：后端 run 状态 + 前端映射${stagesUnavailable ? "（stages 端点不可用）" : ""}`,
    title: `该 run 无阶段级数据（旧后端写入），格子的状态由前端按 run.status 静态映射，不随时间推进；五格与后端的五个推进点一一对应（desktop/src/stages.js）。`,
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
 * done/running；run 未结束且 publish 未完成时，后面的格子按最后已完成的阶段
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
    for (const event of events) {
      const slot = STAGE_TO_SLOT[event.stage];
      if (!slot) continue;
      if (event.finished_at) {
        states[slot] = "done";
      } else if (run.status === "running" || run.status === "pending") {
        states[slot] = "running";
      } else {
        // run 已终止（failed/cancelled）却停在某个阶段：该格标失败
        states[slot] = "error";
      }
    }
    // 每格都有自己的后端阶段事件，所以这里没有要推断的东西：状态就是
    // 事件说的事实。以前有一格（「证据」）在后端没有对应阶段，状态是推断
    // 出来的——那格已经拆掉了。
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
    // 保守映射：采集已完成，Apktool 解析进行中，其余未开始
    states.collect = "done";
    states["parse-apktool"] = "running";
    states.index = "pending";
    states["decompile-jadx"] = "pending";
    states.report = "pending";
    return { states, partialLabels };
  }

  if (run.status === "completed") {
    STAGES.forEach((s) => (states[s.id] = "done"));
    applyPartial(run, states, partialLabels);
    return { states, partialLabels };
  }

  // failed：run 已终止且未发布；把「解析」格标失败（首个非采集阶段）
  states.collect = "done";
  states["parse-apktool"] = "error";
  states.index = "pending";
  states["decompile-jadx"] = "pending";
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
    if (tool.includes("jadx")) affected.add("decompile-jadx");
    if (tool.includes("apktool")) affected.add("parse-apktool");
    if (tool.includes("androguard")) affected.add("index");
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
 * 【三份事实，各管一件事】
 * - `run.tool_versions`：这一轮**记下了哪些版本**（后端事实，run 的记录）；
 * - `machine.missing`：本机**装没装**（后端事实，GET /api/backends）；
 * - `run.status`：这一轮**还在不在跑**（后端事实，run 的状态字段）。
 *
 * 【为什么要机器那份名单】`tool_versions` 的值可能是 null，而这有两种完全
 * 不同的意思：还没探测出来，或者压根没装。run 的记录分不开这两件事——它只
 * 记了键，键在而值为空。分不开就要说错，而两头都实测说错过：
 * - 分析进行中、键还没写进去时，三个后端全被说成「未安装」（装着的后端被
 *   说没装）——那是上一轮修复前的现象，管道现在会在探测前先把名字写下去；
 * - 分析结束、后端确实没装时，仍被说成「版本探测中」（没装的后端被说成正
 *   在探测）——探测早就结束了，值还是 null。
 * 机器那份名单是唯一能分开的证据：它回答的就是「装没装」。
 *
 * 【为什么不说「版本探测中」】探测只发生在分析的头几秒；分析还在跑的时候
 * 探测多半早就结束了，这时候再说「探测中」是说谎。所以活着的 run 一律说
 * 「版本尚未记录」——探测中与探测失败，这句话都对。
 *
 * @typedef {import("./types").BackendState} BackendState
 * @typedef {import("./types").BackendStatus} BackendStatus
 * @typedef {{missing?: string[], available?: string[], versions?: Record<string, string | null>}} MachineBackends
 */

/** 页面右栏的三个后端，顺序即页面上的顺序。 @type {Array<{name: string, key: string}>} */
export const BACKEND_KEYS = [
  { name: "JADX", key: "jadx" },
  { name: "Apktool", key: "apktool" },
  { name: "Androguard", key: "androguard" },
];

/**
 * 从最近一轮 run 的 tool_versions 与机器的后端名单推断三个后端的状态。
 *
 * @param {{status?: string, tool_versions?: Record<string, string | null>} | null} run 最近一轮分析（没有就 null）
 * @param {MachineBackends | null} [machine] GET /api/backends 的回答；拿不到就 null
 * @returns {BackendStatus[]}
 */
export function deriveBackends(run, machine) {
  const missing = new Set((machine && machine.missing) || []);
  const versions = (run && run.tool_versions) || {};
  const status = run ? run.status : undefined;
  const live = Boolean(run) && !isTerminalStatus(status);
  return BACKEND_KEYS.map(({ name, key }) => {
    if (!run) {
      return { name, state: "queued", detail: "等待分析轮次数据…" };
    }
    if (!(key in versions)) {
      // 这一轮没有记下这个后端。
      if (missing.has(key)) {
        return { name, state: "error", detail: "未安装或未配置，未参与本次分析" };
      }
      if (live) {
        return { name, state: "running", detail: "参与本次分析 · 版本尚未记录" };
      }
      return { name, state: "error", detail: "本次分析未记录该后端的参与情况" };
    }
    const version = versions[key];
    if (version) {
      return { name, state: "done", detail: `v${version} · 参与本次分析` };
    }
    // 键在、值为空：这一轮带着这个后端，但版本还没记下来。
    if (missing.has(key)) {
      // 机器上说它没装：它压根不会参与，版本也永远不会有。
      return { name, state: "error", detail: "未安装或未配置，未参与本次分析" };
    }
    if (live) {
      return { name, state: "running", detail: "参与本次分析 · 版本尚未记录" };
    }
    return { name, state: "error", detail: "版本未知：本次分析没有记下该后端的版本" };
  });
}
