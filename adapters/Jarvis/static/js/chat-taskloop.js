// ═══════════════════════════════════════════════════════════════════════════
// chat-taskloop.js — TRION Task-Loop Pipeline Viewer
// ═══════════════════════════════════════════════════════════════════════════
//
// Renders an animated, collapsible pipeline view for Task-Loop execution.
// Each pipeline stage becomes a live block that streams content as it runs.
//
// Block types (in order):
//   • plan        — Initial plan overview (steps list)
//   • thinking    — ThinkingLayer reasoning stream (live)
//   • tool        — Tool call with args + result
//   • transition  — Single-line bridge between steps (auto, not collapsible)
//   • reflection  — Loop reflection / self-correction
//   • finish      — Final status
//
// ═══════════════════════════════════════════════════════════════════════════

import { log } from "./debug.js";

// ─── Internal State ────────────────────────────────────────────────────────

const _loops = new Map(); // loopId → LoopState

function _esc(s) {
    return String(s ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _lucide() {
    if (window.lucide) {
        window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide" });
    }
}

function _scrollChat() {
    const c = document.getElementById("chat-container");
    if (c) c.scrollTop = c.scrollHeight;
}

// ─── Block config ──────────────────────────────────────────────────────────

const BLOCK_CONFIG = {
    plan:       { icon: "list-checks",    color: "tl-color-plan",       label: "Plan" },
    thinking:   { icon: "brain",          color: "tl-color-thinking",   label: "Thinking" },
    tool:       { icon: "wrench",         color: "tl-color-tool",       label: "Tool Call" },
    reflection: { icon: "telescope",      color: "tl-color-reflection", label: "Reflection" },
    finish:     { icon: "check-circle-2", color: "tl-color-finish",     label: "Finished" },
    error:      { icon: "x-circle",       color: "tl-color-error",      label: "Error" },
};

// ─── Loader (TRION triangle spinner) ──────────────────────────────────────

function _makeLoader(id) {
    return `
    <div class="tl-loader" id="${id}-loader" aria-hidden="true">
        <div class="tl-triangle">
            <span class="tl-dot tl-dot-a"></span>
            <span class="tl-dot tl-dot-b"></span>
            <span class="tl-dot tl-dot-c"></span>
        </div>
    </div>`;
}

function _removeLoader(loopId) {
    const el = document.getElementById(`${loopId}-loader`);
    if (el) el.remove();
}

// ─── Loop Container ────────────────────────────────────────────────────────

/**
 * Create the top-level Work container that wraps all pipeline blocks.
 * Collapsed by default, arrow toggle opens it.
 *
 * @param {string|number} messageId
 * @returns {string} loopId
 */
export function createTaskLoopView(messageId) {
    const container = document.getElementById("messages-list");
    const welcome   = document.getElementById("welcome-message");
    if (!container) return null;
    if (welcome) welcome.classList.add("hidden");

    const loopId = `taskloop-${messageId}`;

    _loops.set(loopId, {
        blockCount: 0,
        activeBlockId: null,
        activeThinkingBlockId: null,
        activeContentBlockId: null,
        planBlockId: null,
        finishBlockId: null,
        finished: false,
        hasError: false,
        stepsDone: 0,
        stepsTotal: 0,
        pendingStepType: "thinking",
        pendingStepTitle: "",
    });

    const wrapper = document.createElement("div");
    wrapper.id    = loopId;
    wrapper.className = "tl-wrapper fade-in";

    wrapper.innerHTML = `
        <div class="tl-header">
            <div class="tl-header-left">
                ${_makeLoader(loopId)}
                <span class="tl-work-label">Work</span>
            </div>
            <button class="tl-toggle" aria-expanded="false" data-target="${loopId}-body" title="Expand / Collapse">
                <i data-lucide="chevron-down" class="w-3 h-3"></i>
            </button>
        </div>
        <div class="tl-body" id="${loopId}-body" aria-hidden="true">
            <div class="tl-blocks" id="${loopId}-blocks"></div>
        </div>
        <div class="tl-footer" id="${loopId}-footer"></div>
    `;

    container.appendChild(wrapper);

    // Toggle handler
    wrapper.querySelector(".tl-toggle").addEventListener("click", () => {
        const btn  = wrapper.querySelector(".tl-toggle");
        const body = document.getElementById(`${loopId}-body`);
        const isOpen = body.classList.toggle("tl-body--open");
        btn.setAttribute("aria-expanded", String(isOpen));
        btn.classList.toggle("tl-toggle--open", isOpen);
    });

    _lucide();
    _scrollChat();
    return loopId;
}

// ─── Block Creation ────────────────────────────────────────────────────────

function _addBlock(loopId, type, label, initialContent = "") {
    const state = _loops.get(loopId);
    if (!state) return null;

    // Auto-open body when first block arrives
    const body = document.getElementById(`${loopId}-body`);
    if (body && !body.classList.contains("tl-body--open")) {
        body.classList.add("tl-body--open");
        const btn = document.querySelector(`#${loopId} .tl-toggle`);
        if (btn) {
            btn.setAttribute("aria-expanded", "true");
            btn.classList.add("tl-toggle--open");
        }
    }

    const cfg     = BLOCK_CONFIG[type] || BLOCK_CONFIG.thinking;
    const blockId = `${loopId}-block-${++state.blockCount}`;
    state.activeBlockId = blockId;

    const blocksEl = document.getElementById(`${loopId}-blocks`);
    if (!blocksEl) return null;

    const block = document.createElement("div");
    block.id        = blockId;
    block.className = `tl-block tl-block--${type} fade-in`;
    block.dataset.type = type;

    block.innerHTML = `
        <details class="tl-details">
            <summary class="tl-summary">
                <i data-lucide="${cfg.icon}" class="tl-block-icon ${cfg.color} tl-icon-pulse"></i>
                <span class="tl-block-label ${cfg.color}">${_esc(label)}</span>
                <span class="tl-block-badge" id="${blockId}-badge"></span>
                <i data-lucide="chevron-right" class="tl-chevron w-3 h-3 ml-auto"></i>
            </summary>
            <div class="tl-block-body" id="${blockId}-body">
                ${initialContent
                    ? `<div class="tl-block-content" id="${blockId}-content">${_esc(initialContent)}</div>`
                    : `<div class="tl-block-stream" id="${blockId}-stream"></div>`
                }
            </div>
        </details>
    `;

    blocksEl.appendChild(block);
    _lucide();
    _scrollChat();
    return blockId;
}

// ─── Transition (non-collapsible connector line) ───────────────────────────

function _addTransition(loopId, text) {
    const blocksEl = document.getElementById(`${loopId}-blocks`);
    if (!blocksEl) return;

    const tr = document.createElement("div");
    tr.className = "tl-transition";
    tr.innerHTML = `
        <span class="tl-transition-line"></span>
        <span class="tl-transition-text">${_esc(text)}</span>
        <span class="tl-transition-line"></span>
    `;
    blocksEl.appendChild(tr);
    _scrollChat();
}

// ─── Public API ────────────────────────────────────────────────────────────

/**
 * Called when task_loop_started arrives.
 * Renders the initial plan block with step list.
 */
export function onTaskLoopStarted(loopId, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const tl    = _taskLoopPayload(payload);
    const steps = Array.isArray(tl.current_plan) ? tl.current_plan : [];
    const topic = String(tl.objective_summary || tl.pending_step || "Running…");

    state.stepsTotal = steps.length;

    const stepsHtml = steps.length
        ? `<ul class="tl-plan-list">${steps.map((s, i) =>
            `<li class="tl-plan-item" id="${loopId}-planstep-${i}">
                <span class="tl-plan-dot">○</span>
                <span class="tl-plan-text">${_esc(s)}</span>
            </li>`).join("")}</ul>`
        : `<p class="tl-stream-text">${_esc(topic)}</p>`;

    let blockId = state.planBlockId;
    if (!blockId) {
        blockId = _addBlock(loopId, "plan", "Plan", "");
        state.planBlockId = blockId;
    }
    if (!blockId) return;

    const streamEl = document.getElementById(`${blockId}-stream`);
    if (streamEl) streamEl.innerHTML = stepsHtml;

    _finalizeBlockIcon(blockId, "plan", false);
    _updateLoopHeader(loopId);
}

/**
 * Called when a new step starts (thinking, tool, etc.)
 */
export function onStepStarted(loopId, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const tl = _taskLoopPayload(payload);
    state.pendingStepTitle = String(tl.pending_step || payload?.pending_step || "Step");
    state.pendingStepType = _inferStepType(payload);
    state.activeThinkingBlockId = null;
    state.activeContentBlockId = null;
    state.activeBlockId = null;

    _updateLoopHeader(loopId);
    _updatePlanStepHighlight(loopId, payload);
}

/**
 * Stream step content into the active block
 */
export function onThinkingStream(loopId, chunk) {
    const state = _loops.get(loopId);
    if (!chunk) return;
    const blockId = _ensureThinkingBlock(loopId);
    if (!blockId) return;
    _appendToBlock(blockId, chunk);
}

/**
 * Stream visible step output into its own block.
 */
export function onStepContent(loopId, chunk) {
    const state = _loops.get(loopId);
    if (!state) return;
    if (!chunk) return;
    const blockId = _ensureContentBlock(loopId);
    if (!blockId) return;
    _appendToBlock(blockId, chunk);
}

/**
 * Called when a step completes — adds a transition line
 */
export function onStepCompleted(loopId, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const tl        = _taskLoopPayload(payload);
    const completed = Array.isArray(tl.completed_steps) ? tl.completed_steps : [];
    const pending   = String(tl.pending_step || "");
    const summary = String(
        payload?.step_summary ||
        payload?.answer_summary ||
        tl?.last_step_result?.user_visible_summary ||
        ""
    );

    const contentBlockId = state.activeContentBlockId;
    const thinkingBlockId = state.activeThinkingBlockId;
    const badgeTarget = contentBlockId || thinkingBlockId;

    for (const blockId of [thinkingBlockId, contentBlockId]) {
        if (!blockId) continue;
        _finalizeBlockIcon(blockId, null, false);
        setTimeout(() => {
            const details = document.querySelector(`#${blockId} details`);
            if (details) details.open = false;
        }, 800);
    }

    if (badgeTarget) {
        if (summary) {
            const badge = document.getElementById(`${badgeTarget}-badge`);
            if (badge) badge.textContent = summary.length > 50 ? summary.slice(0, 50) + "…" : summary;
        }
    }
    state.activeBlockId = null;
    state.activeThinkingBlockId = null;
    state.activeContentBlockId = null;

    state.stepsDone = completed.length;
    _updateLoopHeader(loopId);
    _updatePlanStepHighlight(loopId, payload);

    if (pending && !payload?.is_final) {
        const transText = summary
            ? `→ ${summary.length > 60 ? summary.slice(0, 60) + "…" : summary}`
            : `→ Next: ${pending.length > 50 ? pending.slice(0, 50) + "…" : pending}`;
        _addTransition(loopId, transText);
    }
}

/**
 * Called on task_loop_reflection event
 */
export function onReflection(loopId, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const tl = _taskLoopPayload(payload);
    const reflection = payload?.event_data?.reflection || payload?.reflection || {};
    const text = String(
        payload?.reflection_text ||
        payload?.event_data?.reflection_text ||
        reflection?.detail ||
        tl?.last_step_result?.trace_reason ||
        tl?.pending_step ||
        payload?.content || ""
    );
    if (!text.trim()) return;

    const blockId = _addBlock(loopId, "reflection", "Reflection");
    if (!blockId) return;

    const streamEl = document.getElementById(`${blockId}-stream`);
    if (streamEl) {
        streamEl.className = "tl-block-stream";
        streamEl.textContent = text || "Evaluating progress…";
    }

    _finalizeBlockIcon(blockId, "reflection", false);

    setTimeout(() => {
        const details = document.querySelector(`#${blockId} details`);
        if (details) details.open = false;
    }, 1200);
}

/**
 * Finalize the entire loop (completed or error)
 */
export function onTaskLoopFinished(loopId, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const doneReason = String(payload?.done_reason || "task_loop_completed");
    const isError    = doneReason !== "task_loop_completed";
    const finishText = String(payload?.content || "").trim();

    if (state.finished && state.finishBlockId) {
        if (!finishText) return;
        const streamEl = document.getElementById(`${state.finishBlockId}-stream`);
        if (streamEl) {
            streamEl.className = "tl-block-stream";
            streamEl.textContent = finishText;
        }
        _scrollChat();
        return;
    }

    state.finished = true;
    state.hasError   = isError;

    _removeLoader(loopId);

    if (state.activeBlockId) {
        _finalizeBlockIcon(state.activeBlockId, null, false);
        state.activeBlockId = null;
    }

    const type    = isError ? "error" : "finish";
    const cfg     = BLOCK_CONFIG[type];
    const blockId = _addBlock(loopId, type, cfg.label);
    state.finishBlockId = blockId;

    if (blockId) {
        const streamEl = document.getElementById(`${blockId}-stream`);
        if (streamEl) {
            streamEl.className = "tl-block-stream";
            const reasonLabel = _doneReasonLabel(doneReason);
            streamEl.textContent = finishText || reasonLabel;
        }
        _finalizeBlockIcon(blockId, type, false);

        if (!isError) {
            setTimeout(() => {
                const details = document.querySelector(`#${blockId} details`);
                if (details) details.open = false;
            }, 2000);
        }
    }

    _updateLoopHeader(loopId, true);
    _scrollChat();
}

// ─── task_loop_update router ───────────────────────────────────────────────

export function handleTaskLoopUpdate(loopId, eventType, payload) {
    const state = _loops.get(loopId);
    if (!state) return;

    const doneReason = String(payload?.done_reason || "");
    const resolvedType = eventType || doneReason;

    switch (resolvedType) {
        case "task_loop_started":
            onTaskLoopStarted(loopId, payload);
            break;
        case "task_loop_plan_updated":
            onTaskLoopStarted(loopId, payload);
            break;
        case "task_loop_step_started":
            onStepStarted(loopId, payload);
            break;
        case "task_loop_step_answered":
            // Step text already arrives over normal content chunks and is
            // mirrored into the active block by chat.js.
            break;
        case "task_loop_step_completed":
            onStepCompleted(loopId, payload);
            break;
        case "task_loop_reflection":
            onReflection(loopId, payload);
            break;
        case "task_loop_completed":
        case "task_loop_cancelled":
        case "task_loop_blocked":
        case "task_loop_waiting_for_user":
        case "task_loop_risk_gate_required":
            onTaskLoopFinished(loopId, { ...payload, done_reason: resolvedType });
            break;
        default:
            if (payload?.is_final) {
                onTaskLoopFinished(loopId, payload);
            }
            break;
    }
}

// ─── Helpers ───────────────────────────────────────────────────────────────

function _inferStepType(payload) {
    const tl   = _taskLoopPayload(payload);
    const step = String(tl.pending_step || "").toLowerCase();
    const kind = String(
        tl.step_kind ||
        payload?.step_kind ||
        payload?.step_runtime?.step_type ||
        ""
    ).toLowerCase();

    if (kind === "tool" || kind === "tool_call" || kind === "tool_request") return "tool";
    if (kind === "think" || kind === "reasoning" || kind === "analysis") return "thinking";
    if (/tool|call|fetch|search|run|exec|invent|inspect|request/.test(step)) return "tool";
    return "thinking";
}

function _ensureThinkingBlock(loopId) {
    const state = _loops.get(loopId);
    if (!state) return null;
    if (state.activeThinkingBlockId) return state.activeThinkingBlockId;
    const blockId = _addBlock(loopId, "thinking", "Thinking");
    if (!blockId) return null;
    state.activeThinkingBlockId = blockId;
    state.activeBlockId = blockId;
    const badge = document.getElementById(`${blockId}-badge`);
    if (badge) {
        const stepTitle = String(state.pendingStepTitle || "Step");
        badge.textContent = stepTitle.length > 40 ? stepTitle.slice(0, 40) + "…" : stepTitle;
    }
    return blockId;
}

function _ensureContentBlock(loopId) {
    const state = _loops.get(loopId);
    if (!state) return null;
    if (state.activeContentBlockId) return state.activeContentBlockId;
    const isTool = String(state.pendingStepType || "").toLowerCase() === "tool";
    const blockId = _addBlock(loopId, isTool ? "tool" : "thinking", isTool ? "Tool Call" : "Step");
    if (!blockId) return null;
    state.activeContentBlockId = blockId;
    state.activeBlockId = blockId;
    const badge = document.getElementById(`${blockId}-badge`);
    if (badge) {
        const stepTitle = String(state.pendingStepTitle || "Step");
        badge.textContent = stepTitle.length > 40 ? stepTitle.slice(0, 40) + "…" : stepTitle;
    }
    return blockId;
}

function _appendToBlock(blockId, chunk) {
    const streamEl = document.getElementById(`${blockId}-stream`);
    if (!streamEl) return;
    if (!streamEl.classList.contains("tl-block-stream")) {
        streamEl.className = "tl-block-stream";
    }
    streamEl.textContent += chunk;
    streamEl.scrollTop = streamEl.scrollHeight;
    _scrollChat();
}

function _finalizeBlockIcon(blockId, type, pulse = false) {
    if (!blockId) return;
    const iconEl = document.querySelector(`#${blockId} .tl-block-icon`);
    if (!iconEl) return;
    iconEl.classList.toggle("tl-icon-pulse", pulse);
    iconEl.classList.toggle("tl-icon-done", !pulse);
}

function _updateLoopHeader(loopId, finished = false) {
    const state  = _loops.get(loopId);
    if (!state) return;

    const label  = document.querySelector(`#${loopId} .tl-work-label`);
    if (!label) return;

    if (finished && !state.hasError) {
        label.textContent = "Work — Done";
        label.classList.add("tl-work-done");
    } else if (finished && state.hasError) {
        label.textContent = "Work — Stopped";
        label.classList.add("tl-work-error");
    } else if (state.stepsTotal > 0) {
        label.textContent = `Work — Step ${state.stepsDone + 1} / ${state.stepsTotal}`;
    }
}

function _updatePlanStepHighlight(loopId, payload) {
    const tl        = _taskLoopPayload(payload);
    const completed = new Set(Array.isArray(tl.completed_steps) ? tl.completed_steps : []);
    const pending   = String(tl.pending_step || "");
    const planSteps = Array.isArray(tl.current_plan) ? tl.current_plan : [];

    planSteps.forEach((step, i) => {
        const el = document.getElementById(`${loopId}-planstep-${i}`);
        if (!el) return;

        const dot  = el.querySelector(".tl-plan-dot");
        const text = el.querySelector(".tl-plan-text");

        if (completed.has(step)) {
            if (dot)  dot.textContent = "✓";
            if (dot)  dot.className = "tl-plan-dot tl-plan-dot--done";
            if (text) text.classList.add("tl-plan-text--done");
        } else if (step === pending) {
            if (dot)  dot.textContent = "◉";
            if (dot)  dot.className = "tl-plan-dot tl-plan-dot--running";
            if (text) text.classList.add("tl-plan-text--running");
        }
    });
}

function _taskLoopPayload(payload) {
    if (payload?.task_loop && typeof payload.task_loop === "object") {
        return payload.task_loop;
    }
    if (payload?.event_data && typeof payload.event_data === "object") {
        return payload.event_data;
    }
    return payload || {};
}

function _doneReasonLabel(reason) {
    const map = {
        "task_loop_completed":              "All steps completed successfully.",
        "task_loop_cancelled":              "Cancelled.",
        "task_loop_blocked":                "Blocked — could not proceed.",
        "task_loop_waiting_for_user":       "Waiting for your input.",
        "task_loop_risk_gate_required":     "Approval required before continuing.",
    };
    return map[reason] || reason;
}

export function hasActiveTaskLoop(loopId) {
    const state = _loops.get(loopId);
    return Boolean(state && !state.finished);
}
