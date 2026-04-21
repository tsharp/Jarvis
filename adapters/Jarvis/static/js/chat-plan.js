import { log } from "./debug.js";

const planState = new Map(); // planId -> { count: number, hasError: boolean, finished: boolean }

// ─── Task-Loop live view ─────────────────────────────────────────────────────
// Separate from the generic plan-event approach: task_loop_update events get
// a live step-list view that updates in place instead of appending new rows.

const taskLoopViewState = new Map(); // planId -> { planLength, stepEls: Map<title, el> }

function _esc(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function _stepIcon(status) {
    if (status === "completed")            return '<span class="text-green-400 font-bold">✓</span>';
    if (status === "running")              return '<span class="text-blue-400 animate-pulse">◉</span>';
    if (status === "waiting_for_approval") return '<span class="text-yellow-400">⚠</span>';
    if (status === "waiting_for_user")     return '<span class="text-yellow-300">?</span>';
    if (status === "blocked")              return '<span class="text-red-400">✗</span>';
    if (status === "failed")               return '<span class="text-red-400">✗</span>';
    return '<span class="text-gray-600">○</span>';
}

function _stepTextClass(status) {
    if (status === "completed")            return "text-gray-400 line-through";
    if (status === "running")              return "text-blue-200 font-medium";
    if (status === "waiting_for_approval") return "text-yellow-300 font-medium";
    if (status === "waiting_for_user")     return "text-yellow-200";
    if (status === "blocked")              return "text-red-400";
    if (status === "failed")               return "text-red-400";
    return "text-gray-600";
}

function _stepBg(status) {
    if (status === "running")              return "bg-blue-950/30 border border-blue-900/40";
    if (status === "waiting_for_approval") return "bg-yellow-950/30 border border-yellow-900/40";
    if (status === "waiting_for_user")     return "bg-yellow-950/20 border border-yellow-900/30";
    if (status === "blocked" || status === "failed") return "bg-red-950/20 border border-red-900/30";
    return "";
}

function _resolveStepStatus(stepTitle, completedSteps, pendingStep, currentStepStatus, isFinal, doneReason) {
    if (completedSteps.has(stepTitle)) return "completed";
    if (stepTitle !== pendingStep)     return "pending";
    // Current step
    if (isFinal) {
        if (doneReason === "task_loop_completed")          return "completed";
        if (doneReason === "task_loop_risk_gate_required") return "waiting_for_approval";
        if (doneReason === "task_loop_user_decision_required") return "waiting_for_user";
        return currentStepStatus || "blocked";
    }
    return "running";
}

function updateTaskLoopView(planId, payload) {
    const stepsEl  = document.getElementById(`${planId}-steps`);
    const titleEl  = document.getElementById(`${planId}-title`);
    const iconEl   = document.querySelector(`#${planId} summary [data-lucide]`);
    if (!stepsEl) return;

    const tl = (payload.task_loop && typeof payload.task_loop === "object") ? payload.task_loop : {};
    const isFinal       = Boolean(payload.is_final);
    const doneReason    = String(payload.done_reason || "");
    const currentPlan   = Array.isArray(tl.current_plan) ? tl.current_plan : [];
    const completedSet  = new Set(Array.isArray(tl.completed_steps) ? tl.completed_steps : []);
    const pendingStep   = String(tl.pending_step || "");
    const stepStatus    = String(tl.current_step_status || "");
    const stepRuntime   = (payload.step_runtime && typeof payload.step_runtime === "object") ? payload.step_runtime : {};
    const planStepsMeta = Array.isArray(tl.plan_steps) ? tl.plan_steps : [];

    // ── Header title + icon ──────────────────────────────────────────────────
    if (titleEl) {
        if (isFinal) {
            if (doneReason === "task_loop_completed") {
                titleEl.innerHTML = '<span class="text-green-400">Task-Loop abgeschlossen</span>';
                if (iconEl) { iconEl.setAttribute("data-lucide", "check-circle-2"); iconEl.classList.remove("animate-pulse"); iconEl.classList.add("text-green-400"); }
            } else if (doneReason === "task_loop_risk_gate_required") {
                titleEl.innerHTML = '<span class="text-yellow-400">Freigabe erforderlich</span>';
                if (iconEl) { iconEl.setAttribute("data-lucide", "shield-alert"); iconEl.classList.remove("animate-pulse"); iconEl.classList.add("text-yellow-400"); }
            } else if (doneReason === "task_loop_user_decision_required") {
                titleEl.innerHTML = '<span class="text-yellow-300">Wartet auf Eingabe</span>';
                if (iconEl) { iconEl.setAttribute("data-lucide", "message-circle-question"); iconEl.classList.remove("animate-pulse"); iconEl.classList.add("text-yellow-300"); }
            } else {
                titleEl.innerHTML = `<span class="text-orange-400">Task-Loop gestoppt</span>`;
                if (iconEl) { iconEl.setAttribute("data-lucide", "circle-stop"); iconEl.classList.remove("animate-pulse"); }
            }
        } else {
            titleEl.textContent = "Task-Loop aktiv";
        }
        if (window.lucide) window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide" });
    }

    if (!currentPlan.length) return;

    // ── Build step list (once), then update each step's status ───────────────
    const vs = taskLoopViewState.get(planId);
    if (!vs || vs.planLength !== currentPlan.length) {
        stepsEl.innerHTML = "";
        const stepEls = new Map();
        currentPlan.forEach((title, idx) => {
            const el = document.createElement("details");
            el.id = `${planId}-step-${idx}`;
            stepsEl.appendChild(el);
            stepEls.set(title, el);
        });
        taskLoopViewState.set(planId, { planLength: currentPlan.length, stepEls });
    }

    const sv = taskLoopViewState.get(planId);
    if (!sv) return;

    // Build capability lookup from plan_steps metadata
    const capabilityMap = new Map();
    planStepsMeta.forEach(s => {
        if (s?.title && s?.requested_capability) {
            const cap = s.requested_capability;
            capabilityMap.set(s.title, cap.capability_action || cap.capability_type || "");
        }
    });

    currentPlan.forEach((stepTitle, idx) => {
        const el = sv.stepEls.get(stepTitle);
        if (!el) return;

        const status = _resolveStepStatus(stepTitle, completedSet, pendingStep, stepStatus, isFinal, doneReason);
        const isCurrentStep = stepTitle === pendingStep;
        const capability = capabilityMap.get(stepTitle) || "";

        // Step type label (only for current running/waiting steps)
        const runtimeType = isCurrentStep ? (stepRuntime.step_type || "") : "";
        const showType = runtimeType && runtimeType !== "analysis" && !completedSet.has(stepTitle);

        // Summary label: state-aware prefix + step title
        const labelPrefix = {
            completed:            `Schritt ${idx + 1} abgeschlossen`,
            running:              `Schritt ${idx + 1} läuft`,
            waiting_for_approval: `Schritt ${idx + 1} wartet auf Freigabe`,
            waiting_for_user:     `Schritt ${idx + 1} wartet auf Eingabe`,
            blocked:              `Schritt ${idx + 1} blockiert`,
            failed:               `Schritt ${idx + 1} fehlgeschlagen`,
        }[status] ?? `Schritt ${idx + 1}`;

        // Auto-open for active/waiting steps; close completed/pending
        const shouldBeOpen = status === "running" || status === "waiting_for_approval" || status === "waiting_for_user";
        el.open = shouldBeOpen;

        el.className = `rounded-lg text-xs transition-all duration-200 ${_stepBg(status)}`;
        el.innerHTML = `
            <summary class="flex items-center gap-2 px-2 py-1.5 cursor-pointer list-none select-none">
                <span class="w-4 flex-shrink-0 text-center leading-none">${_stepIcon(status)}</span>
                <span class="${_stepTextClass(status)} leading-relaxed break-words flex-1">
                    ${_esc(labelPrefix)}: <span class="opacity-80">${_esc(stepTitle)}</span>
                </span>
            </summary>
            <div class="px-8 pb-2 pt-0.5 space-y-1 text-[11px] text-gray-500">
                ${capability ? `<div>Tool: <span class="font-mono text-gray-400">${_esc(capability)}</span></div>` : ""}
                ${showType  ? `<div>Typ: <span class="italic">${_esc(runtimeType)}</span></div>` : ""}
                ${status === "waiting_for_approval" ? `<div class="text-yellow-500">→ Schreibe "freigeben" um fortzufahren</div>` : ""}
                ${status === "waiting_for_user"     ? `<div class="text-yellow-400">→ Warte auf deine Eingabe</div>` : ""}
            </div>
        `;
    });

    ensureAutoScroll();
}

function esc(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function toText(payload) {
    if (!payload || typeof payload !== "object") return "";
    const lines = [];
    for (const [key, value] of Object.entries(payload)) {
        if (value === undefined || value === null || value === "") continue;
        if (typeof value === "object") {
            try {
                lines.push(`${key}: ${JSON.stringify(value)}`);
            } catch {
                lines.push(`${key}: [object]`);
            }
            continue;
        }
        lines.push(`${key}: ${String(value)}`);
    }
    return lines.join("\n");
}

function buildEventView(eventType, payload) {
    const p = payload && typeof payload === "object" ? payload : {};
    if (eventType === "planning_start") {
        return {
            title: "Master Planning gestartet",
            badge: "start",
            detail: toText({
                objective: p.objective,
                max_loops: p.max_loops,
                state: p.state,
                planning_mode: p.planning_mode,
                summary: p.summary,
            }),
        };
    }
    if (eventType === "planning_step") {
        return {
            title: p.phase ? `Master Schritt (${p.phase})` : "Master Schritt",
            badge: "step",
            detail: toText({
                loop: p.loop,
                decision: p.decision,
                action: p.action,
                next_action: p.next_action,
                reason: p.reason,
                summary: p.summary,
            }),
        };
    }
    if (eventType === "planning_done") {
        return {
            title: "Master Planning abgeschlossen",
            badge: "done",
            detail: toText({
                loops_executed: p.loops_executed,
                steps_completed: p.steps_completed,
                final_state: p.final_state,
                stop_reason: p.stop_reason,
                summary: p.summary,
            }),
        };
    }
    if (eventType === "planning_error") {
        return {
            title: "Master Planning Fehler",
            badge: "error",
            detail: toText({
                phase: p.phase,
                error: p.error,
                error_code: p.error_code,
                action: p.action,
                stop_reason: p.stop_reason,
                summary: p.summary,
            }),
        };
    }
    if (eventType === "sequential_start") {
        return {
            title: "Sequential gestartet",
            badge: "start",
            detail: toText({
                task_id: p.task_id,
                complexity: p.complexity,
                reasoning_type: p.reasoning_type,
            }),
        };
    }
    if (eventType === "sequential_step") {
        return {
            title: `Sequential Step ${p.step_number || p.step_num || p.step || "?"}`,
            badge: "step",
            detail: toText({
                title: p.title,
                thought: p.thought || p.content || p.text,
            }),
        };
    }
    if (eventType === "sequential_done") {
        return {
            title: "Sequential abgeschlossen",
            badge: "done",
            detail: toText({
                task_id: p.task_id,
                summary: p.summary,
                steps: Array.isArray(p.steps) ? p.steps.length : undefined,
            }),
        };
    }
    if (eventType === "sequential_error") {
        return {
            title: "Sequential Fehler",
            badge: "error",
            detail: toText({
                task_id: p.task_id,
                error: p.error,
            }),
        };
    }
    if (eventType === "loop_trace_started") {
        return {
            title: "Loop-Trace gestartet",
            badge: "start",
            detail: toText({
                objective: p.objective,
                intent: p.intent,
                resolution_strategy: p.resolution_strategy,
                suggested_tools: p.suggested_tools,
                needs_memory: p.needs_memory,
                needs_sequential_thinking: p.needs_sequential_thinking,
            }),
        };
    }
    if (eventType === "loop_trace_plan_normalized") {
        return {
            title: "Plan normalisiert",
            badge: "step",
            detail: toText({
                mode: p.mode,
                reason: p.reason,
                resolution_strategy: p.resolution_strategy,
                suggested_tools: p.suggested_tools,
                needs_memory: p.needs_memory,
                corrections: p.corrections,
            }),
        };
    }
    if (eventType === "loop_trace_step_started") {
        return {
            title: p.phase ? `Loop-Schritt (${p.phase})` : "Loop-Schritt",
            badge: "step",
            detail: toText({
                summary: p.summary,
                details: p.details,
            }),
        };
    }
    if (eventType === "loop_trace_correction") {
        return {
            title: "Korrektur angewendet",
            badge: "step",
            detail: toText({
                stage: p.stage,
                summary: p.summary,
                reasons: p.reasons,
                details: p.details,
            }),
        };
    }
    if (eventType === "loop_trace_completed") {
        return {
            title: "Loop-Trace abgeschlossen",
            badge: "done",
            detail: toText({
                response_mode: p.response_mode,
                model: p.model,
                correction_count: p.correction_count,
                summary: p.summary,
            }),
        };
    }
    if (eventType === "task_loop_routing") {
        return {
            title: "Task-Loop Routing",
            badge: String(p.branch || "").includes("task_loop") ? "step" : "done",
            detail: toText({
                execution_mode: p.execution_mode,
                turn_mode: p.turn_mode,
                is_authoritative_task_loop_turn: p.is_authoritative_task_loop_turn,
                active_task_loop_reason: p.active_task_loop_reason,
                branch: p.branch,
                task_loop_candidate: p.task_loop_candidate,
                task_loop_kind: p.task_loop_kind,
                task_loop_confidence: p.task_loop_confidence,
                needs_visible_progress: p.needs_visible_progress,
                task_loop_reason: p.task_loop_reason,
            }),
        };
    }
    if (eventType === "task_loop_update") {
        const state = p.state || "";
        const stepIndex = p.task_loop?.step_index ?? "";
        const pendingStep = p.task_loop?.pending_step || "";
        const doneReason = p.done_reason || "";
        const isFinal = Boolean(p.is_final);

        const badge = isFinal
            ? (doneReason === "task_loop_completed" ? "done" : "warn")
            : "step";

        const title = isFinal
            ? (doneReason === "task_loop_completed"
                ? "Task-Loop abgeschlossen"
                : `Task-Loop gestoppt (${doneReason})`)
            : stepIndex !== ""
                ? `Schritt ${stepIndex}`
                : "Task-Loop läuft";

        return {
            title,
            badge,
            detail: toText({
                state,
                pending_step: pendingStep || undefined,
                done_reason: doneReason || undefined,
            }),
        };
    }
    if (/^task_loop_/.test(eventType)) {
        const labels = {
            task_loop_started: "Task-Loop gestartet",
            task_loop_plan_updated: "Task-Loop Plan aktualisiert",
            task_loop_context_updated: "Task-Loop Kontext aktualisiert",
            task_loop_step_started: "Task-Loop Schritt gestartet",
            task_loop_step_answered: "Task-Loop Schritt beantwortet",
            task_loop_step_completed: "Task-Loop Schritt abgeschlossen",
            task_loop_reflection: "Task-Loop Reflexion",
            task_loop_waiting_for_user: "Task-Loop wartet auf Eingabe",
            task_loop_blocked: "Task-Loop blockiert",
            task_loop_completed: "Task-Loop abgeschlossen",
            task_loop_cancelled: "Task-Loop abgebrochen",
        };
        const badge = (
            eventType === "task_loop_completed" ? "done"
            : eventType === "task_loop_blocked" ? "error"
            : eventType === "task_loop_cancelled" ? "warn"
            : eventType === "task_loop_waiting_for_user" ? "step"
            : "step"
        );
        return {
            title: labels[eventType] || eventType,
            badge,
            detail: toText({
                summary: p.summary || p.content || undefined,
                source_layer: p.source_layer || undefined,
                replay: p.replay || undefined,
            }),
        };
    }
    return {
        title: eventType || "plan_event",
        badge: "step",
        detail: toText(p),
    };
}

function badgeClass(type) {
    if (type === "done") return "text-green-400";
    if (type === "error") return "text-red-400";
    if (type === "start") return "text-blue-400";
    return "text-gray-400";
}

function ensureAutoScroll() {
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
}

function updateHeader(planId) {
    const state = planState.get(planId);
    if (!state) return;
    const statusEl = document.getElementById(`${planId}-status`);
    if (!statusEl) return;

    // For task-loop boxes, show plan length from taskLoopViewState
    const tlvs = taskLoopViewState.get(planId);
    const count = tlvs ? tlvs.planLength : state.count;
    const stepText = count ? `${count} Schritt${count === 1 ? "" : "e"}` : "";

    if (state.hasError) {
        statusEl.innerHTML = `${stepText}${stepText ? " · " : ""}<span class="text-red-400">Fehler</span>`;
    } else if (state.finished) {
        statusEl.innerHTML = `${stepText}${stepText ? " · " : ""}<span class="text-green-400">Fertig</span>`;
    } else {
        statusEl.textContent = stepText || "läuft…";
    }
}

export function createPlanBox(messageId) {
    const container = document.getElementById("messages-list");
    const welcome = document.getElementById("welcome-message");
    if (!container) return null;
    if (welcome) welcome.classList.add("hidden");

    const planId = `plan-${messageId}`;
    planState.set(planId, { count: 0, hasError: false, finished: false });

    const div = document.createElement("div");
    div.id = planId;
    div.className = "fade-in mb-2";
    div.innerHTML = `
        <details open class="bg-dark-card border border-dark-border rounded-xl overflow-hidden">
            <summary class="px-4 py-2 cursor-pointer hover:bg-dark-hover flex items-center gap-2 text-sm text-gray-300">
                <i data-lucide="route" class="w-4 h-4 text-cyan-400 animate-pulse"></i>
                <span id="${planId}-title">Planmodus (live)</span>
                <span id="${planId}-status" class="text-xs text-gray-500 ml-auto">0 Schritte</span>
            </summary>
            <div class="border-t border-dark-border">
                <div id="${planId}-steps" class="px-3 py-3 space-y-2 max-h-96 overflow-y-auto"></div>
            </div>
        </details>
    `;

    container.appendChild(div);
    if (window.lucide) window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide" });
    ensureAutoScroll();
    log("info", `Plan box created: ${planId}`);
    return planId;
}

export function appendPlanEvent(planId, eventType, payload = {}) {
    if (!planId) return;
    const state = planState.get(planId);
    const stepsEl = document.getElementById(`${planId}-steps`);
    if (!state || !stepsEl) return;

    // Task-loop events get a live step-list view, not a <details> block.
    // Handle state flags without incrementing the step counter.
    if (eventType === "task_loop_update") {
        if (Boolean(payload?.is_final) && String(payload?.done_reason || "") !== "task_loop_completed") {
            state.hasError = true;
        }
        if (Boolean(payload?.is_final)) state.finished = true;
        updateTaskLoopView(planId, payload);
        updateHeader(planId);
        return;
    }

    const stepNo = state.count + 1;
    state.count = stepNo;
    if (
        eventType === "planning_error"
        || eventType === "sequential_error"
    ) {
        state.hasError = true;
    }
    if (
        eventType === "planning_done"
        || eventType === "loop_trace_completed"
    ) {
        state.finished = true;
    }

    const view = buildEventView(eventType, payload);
    const detail = String(view.detail || "").trim() || "Keine Details";

    const block = document.createElement("details");
    block.className = "bg-dark-hover/60 border border-dark-border rounded-lg";
    block.innerHTML = `
        <summary class="px-3 py-2 cursor-pointer hover:bg-dark-hover text-xs flex items-center gap-2">
            <span class="text-gray-500">#${stepNo}</span>
            <span class="${badgeClass(view.badge)}">${esc(view.title)}</span>
            <span class="text-gray-600 ml-auto">${esc(eventType)}</span>
        </summary>
        <div class="px-3 pb-3">
            <pre class="text-xs text-gray-300 whitespace-pre-wrap break-words font-mono leading-relaxed">${esc(detail)}</pre>
        </div>
    `;
    stepsEl.appendChild(block);

    updateHeader(planId);
    ensureAutoScroll();
}

export function finalizePlanBox(planId, summary = "") {
    if (!planId) return;
    const state = planState.get(planId);
    if (!state) return;
    state.finished = true;

    // If this is a task-loop box, updateTaskLoopView already set the final title/icon
    // on the is_final event — don't overwrite it here.
    if (!taskLoopViewState.has(planId)) {
        const titleEl = document.getElementById(`${planId}-title`);
        if (titleEl) {
            titleEl.textContent = state.hasError ? "Planmodus (mit Fehlern)" : "Planmodus abgeschlossen";
        }

        const icon = document.querySelector(`#${planId} summary [data-lucide]`);
        if (icon) {
            icon.classList.remove("animate-pulse");
            icon.setAttribute("data-lucide", state.hasError ? "alert-triangle" : "check-circle");
        }
    }

    if (summary) {
        appendPlanEvent(planId, "planning_done", { summary });
    } else {
        updateHeader(planId);
    }

    if (window.lucide) window.lucide.createIcons({ icons: window.lucide.icons, nameAttr: "data-lucide" });
    log("info", `Plan box finalized: ${planId}`);
}
