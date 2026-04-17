const { createApp, ref, computed, onMounted } = Vue;

const AgentPanel = {
    props: ['running'],
    emits: ['start', 'stop', 'screenshot'],
    template: `
        <div class="panel agent-form">
            <label>Задача агента</label>
            <textarea v-model="task" placeholder="Войти в систему и открыть Базу знаний..."></textarea>
            <div class="row">
                <select v-model="provider">
                    <option value="kimi-cli">kimi-cli</option>
                    <option value="openai">openai</option>
                    <option value="anthropic">anthropic</option>
                    <option value="ollama">ollama</option>
                </select>
                <input type="number" v-model.number="maxSteps" min="1" max="100">
            </div>
            <div class="checkbox">
                <input type="checkbox" v-model="textMode" id="agentTextMode">
                <label for="agentTextMode">Text-mode (быстрее, без скриншотов в цикле)</label>
            </div>
            <button v-if="!running" @click="$emit('start', {task, provider, maxSteps, textMode})">▶ Запустить агента</button>
            <button v-else class="stop" @click="$emit('stop')">⏹ Стоп</button>
            <button class="secondary" @click="$emit('screenshot')" style="margin-top:8px;">📷 Скриншот шага</button>
            <div class="section-title">Лента reasoning</div>
            <div class="reasoning-log" ref="log"></div>
        </div>
    `,
    setup() {
        const task = ref('Войти в систему используя email k.tretyakov@slsoft.ru и пароль v_vP5GxCva, затем открыть раздел База знаний');
        const provider = ref('kimi-cli');
        const maxSteps = ref(15);
        const textMode = ref(true);
        return { task, provider, maxSteps, textMode };
    }
};

const StepModal = {
    props: ['visible', 'editIndex', 'initial'],
    emits: ['close', 'save'],
    setup(props, { emit }) {
        const type = ref('click');
        const elementId = ref('');
        const text = ref('');
        const key = ref('');
        const url = ref('');
        const direction = ref('down');
        const seconds = ref(1);
        const showElement = computed(() => ['click','type','hover'].includes(type.value));
        const showText = computed(() => type.value === 'type');
        const showKey = computed(() => type.value === 'press_key');
        const showUrl = computed(() => type.value === 'navigate');
        const showDirection = computed(() => type.value === 'scroll');
        const showSeconds = computed(() => type.value === 'wait');

        const reset = (step) => {
            type.value = step.action_type || 'click';
            elementId.value = step.element_display_id || '';
            text.value = step.text || '';
            key.value = step.key || '';
            url.value = step.url || '';
            direction.value = step.direction || 'down';
            seconds.value = step.seconds != null ? step.seconds : 1;
        };

        const save = () => {
            const action = { action_type: type.value };
            if (showElement.value) {
                const eid = parseInt(elementId.value || '0');
                if (eid) action.element_display_id = eid;
            }
            if (showText.value) action.text = text.value;
            if (showKey.value) action.key = key.value;
            if (showUrl.value) action.url = url.value;
            if (showDirection.value) action.direction = direction.value;
            if (showSeconds.value) action.seconds = parseInt(seconds.value || '0');
            emit('save', action);
        };

        return { type, elementId, text, key, url, direction, seconds, showElement, showText, showKey, showUrl, showDirection, showSeconds, reset, save };
    },
    template: `
        <div class="modal" :class="{active: visible}">
            <div class="modal-content">
                <div class="modal-title">{{ editIndex !== null ? 'Редактировать шаг' : 'Добавить шаг' }}</div>
                <div class="modal-row">
                    <label>Action type</label>
                    <select v-model="type">
                        <option value="click">click</option>
                        <option value="type">type</option>
                        <option value="press_key">press_key</option>
                        <option value="scroll">scroll</option>
                        <option value="navigate">navigate</option>
                        <option value="screenshot">screenshot</option>
                        <option value="wait">wait</option>
                        <option value="hover">hover</option>
                    </select>
                </div>
                <div class="modal-row" v-show="showElement">
                    <label>Element display id</label>
                    <input type="number" v-model="elementId" placeholder="1">
                </div>
                <div class="modal-row" v-show="showText">
                    <label>Text</label>
                    <input type="text" v-model="text" placeholder="Введите текст">
                </div>
                <div class="modal-row" v-show="showKey">
                    <label>Key</label>
                    <input type="text" v-model="key" placeholder="Enter">
                </div>
                <div class="modal-row" v-show="showUrl">
                    <label>URL</label>
                    <input type="text" v-model="url" placeholder="https://...">
                </div>
                <div class="modal-row" v-show="showDirection">
                    <label>Direction</label>
                    <select v-model="direction">
                        <option value="down">down</option>
                        <option value="up">up</option>
                        <option value="left">left</option>
                        <option value="right">right</option>
                    </select>
                </div>
                <div class="modal-row" v-show="showSeconds">
                    <label>Seconds</label>
                    <input type="number" v-model="seconds" min="0">
                </div>
                <div class="modal-btns">
                    <button class="secondary" @click="$emit('close')">Cancel</button>
                    <button @click="save">Save</button>
                </div>
            </div>
        </div>
    `
};

createApp({
    components: { AgentPanel, StepModal },
    setup() {
        const url = ref('https://stagehelper.ai.slsoft.ru/');
        const screenshot = ref('');
        const elements = ref({});
        const status = ref('Загрузка...');
        const activeTab = ref('manual');
        const autoRefreshInterval = ref(null);
        const lastElementDisplayId = ref(null);
        const lastManualAction = ref(null);

        // Scenario state
        const scenarios = ref([]);
        const currentScenarioId = ref(null);
        const autoRecordEnabled = ref(false);
        const replayDelay = ref(0.5);
        const replayRunning = ref(false);
        const stepHighlights = ref({});
        const modalVisible = ref(false);
        const modalEditIndex = ref(null);
        const modalInitial = ref({});

        // Agent state
        const agentRunning = ref(false);
        let ws = null;
        let replayWs = null;

        const currentScenario = computed(() => scenarios.value.find(s => s.id === currentScenarioId.value) || null);

        const apiPost = async (path, body) => {
            const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            return await res.json();
        };
        const apiGet = async (path) => {
            const res = await fetch(path);
            return await res.json();
        };

        const setScreenshot = (base64Url) => {
            const img = new Image();
            img.onload = () => { screenshot.value = img.src; };
            img.src = base64Url;
        };

        const startAutoRefresh = () => {
            stopAutoRefresh();
            autoRefreshInterval.value = setInterval(refreshScreenshot, 3000);
        };
        const stopAutoRefresh = () => {
            if (autoRefreshInterval.value) {
                clearInterval(autoRefreshInterval.value);
                autoRefreshInterval.value = null;
            }
        };

        const refreshScreenshot = async () => {
            const res = await apiPost('/screenshot_annotated', {});
            setScreenshot('data:image/jpeg;base64,' + res.image);
            elements.value = res.elements || {};
            status.value = 'Обновлено: ' + new Date().toLocaleTimeString();
        };

        const navigate = async () => {
            await apiPost('/navigate', { url: url.value });
            await refreshScreenshot();
            lastManualAction.value = { action_type: 'navigate', url: url.value };
            await maybeAutoRecord();
        };

        const enrichAction = (action) => {
            if (action.element_display_id != null) {
                const info = elements.value[action.element_display_id];
                if (info) {
                    action.selector = info.selector || undefined;
                    action.stable_hash = info.stable_hash || undefined;
                }
            }
            return action;
        };

        const sendAction = async (action) => {
            if (action.element_display_id !== undefined) lastElementDisplayId.value = action.element_display_id;
            const enriched = enrichAction({ ...action });
            const result = await apiPost('/act', { action: enriched });
            status.value = result.observation || result.status;
            await refreshScreenshot();
            lastManualAction.value = enriched;
            await maybeAutoRecord();
        };

        const takeScreenshot = async () => {
            await sendAction({ action_type: 'screenshot', filename: 'manual.jpg' });
        };

        const typeText = async () => {
            const text = document.getElementById('typeInput')?.value;
            if (!lastElementDisplayId.value) { alert('Сначала кликните по полю ввода'); return; }
            await sendAction({ action_type: 'type', element_display_id: lastElementDisplayId.value, text });
            document.getElementById('typeInput').value = '';
        };

        const switchTab = (tab) => {
            activeTab.value = tab;
            if (tab === 'manual') startAutoRefresh(); else stopAutoRefresh();
        };

        // Scenarios
        const loadScenarios = async () => {
            const data = await apiGet('/scenario/list');
            if (data.status === 'ok') {
                scenarios.value = data.scenarios || [];
                currentScenarioId.value = data.current_scenario_id || null;
            }
        };

        const selectScenario = async (id) => {
            if (!id) return;
            await apiPost('/scenario/select', { scenario_id: id });
            currentScenarioId.value = id;
        };

        const createScenario = async () => {
            const name = prompt('Название сценария:', 'New scenario');
            if (!name) return;
            const data = await apiPost('/scenario/create', { name });
            if (data.status === 'ok') {
                scenarios.value.push(data.scenario);
                currentScenarioId.value = data.scenario.id;
            }
        };

        const renameScenario = async () => {
            const sc = currentScenario.value;
            if (!sc) return alert('Сначала выберите сценарий');
            const name = prompt('Новое название:', sc.name);
            if (!name) return;
            const data = await apiPost('/scenario/rename', { scenario_id: sc.id, name });
            if (data.status === 'ok') sc.name = name;
        };

        const deleteScenario = async () => {
            const sc = currentScenario.value;
            if (!sc) return;
            if (!confirm(`Удалить сценарий "${sc.name}"?`)) return;
            const data = await apiPost('/scenario/delete', { scenario_id: sc.id });
            if (data.status === 'ok') {
                scenarios.value = scenarios.value.filter(s => s.id !== sc.id);
                currentScenarioId.value = data.current_scenario_id;
            }
        };

        const toggleAutoRecord = () => {
            autoRecordEnabled.value = !autoRecordEnabled.value;
        };

        const maybeAutoRecord = async () => {
            if (!autoRecordEnabled.value || !lastManualAction.value || !currentScenarioId.value) return;
            const data = await apiPost('/scenario/step/add', { scenario_id: currentScenarioId.value, action: lastManualAction.value });
            if (data.status === 'ok' && currentScenario.value) {
                currentScenario.value.steps.push(lastManualAction.value);
            }
        };

        const recordLastAction = async () => {
            if (!lastManualAction.value || !currentScenarioId.value) return;
            const data = await apiPost('/scenario/step/add', { scenario_id: currentScenarioId.value, action: lastManualAction.value });
            if (data.status === 'ok' && currentScenario.value) {
                currentScenario.value.steps.push(lastManualAction.value);
            }
        };

        const moveStep = async (index, direction) => {
            const sc = currentScenario.value;
            if (!sc) return;
            const data = await apiPost('/scenario/step/move', { scenario_id: sc.id, step_index: index, direction });
            if (data.status === 'ok') {
                const temp = sc.steps[index];
                sc.steps[index] = sc.steps[index + direction];
                sc.steps[index + direction] = temp;
            }
        };

        const duplicateStep = async (index) => {
            const sc = currentScenario.value;
            if (!sc) return;
            const data = await apiPost('/scenario/step/duplicate', { scenario_id: sc.id, step_index: index });
            if (data.status === 'ok') {
                sc.steps.splice(index + 1, 0, JSON.parse(JSON.stringify(sc.steps[index])));
            }
        };

        const deleteStep = async (index) => {
            const sc = currentScenario.value;
            if (!sc) return;
            if (!confirm('Удалить шаг?')) return;
            const data = await apiPost('/scenario/step/delete', { scenario_id: sc.id, step_index: index });
            if (data.status === 'ok') sc.steps.splice(index, 1);
        };

        const formatStepInfo = (step) => {
            const parts = [step.action_type];
            if (step.element_display_id != null) parts.push(`#${step.element_display_id}`);
            if (step.text) parts.push(`"${step.text}"`);
            if (step.key) parts.push(`key:${step.key}`);
            if (step.url) parts.push(step.url);
            if (step.direction) parts.push(step.direction);
            if (step.seconds != null) parts.push(`${step.seconds}s`);
            return parts.join(' ');
        };

        const openModal = (index, step) => {
            modalEditIndex.value = index;
            modalInitial.value = step ? { ...step } : { action_type: 'click' };
            modalVisible.value = true;
        };

        const closeModal = () => {
            modalVisible.value = false;
            modalEditIndex.value = null;
        };

        const saveModal = async (action) => {
            const sc = currentScenario.value;
            if (!sc) return;
            if (modalEditIndex.value !== null) {
                const data = await apiPost('/scenario/step/update', { scenario_id: sc.id, step_index: modalEditIndex.value, action });
                if (data.status === 'ok') sc.steps[modalEditIndex.value] = action;
            } else {
                const data = await apiPost('/scenario/step/add', { scenario_id: sc.id, action });
                if (data.status === 'ok') sc.steps.push(action);
            }
            closeModal();
        };

        const clearHighlights = () => {
            stepHighlights.value = {};
        };

        const startReplay = () => {
            const sc = currentScenario.value;
            if (!sc || sc.steps.length === 0) return alert('Нет шагов для воспроизведения');
            if (replayWs) replayWs.close();
            clearHighlights();
            replayRunning.value = true;
            status.value = 'Replay running...';
            replayWs = new WebSocket('ws://' + location.host + '/ws/replay');
            replayWs.onopen = () => {
                replayWs.send(JSON.stringify({ scenario_id: sc.id, delay: parseFloat(replayDelay.value) || 0 }));
            };
            replayWs.onmessage = (e) => {
                const data = JSON.parse(e.data);
                switch (data.type) {
                    case 'step_start':
                        stepHighlights.value = { ...stepHighlights.value, [data.index]: 'active-step' };
                        break;
                    case 'screenshot':
                        if (data.image) {
                            setScreenshot('data:image/jpeg;base64,' + data.image);
                            if (data.elements) elements.value = data.elements;
                        }
                        break;
                    case 'step_result':
                        stepHighlights.value = { ...stepHighlights.value, [data.index]: data.error ? 'step-error' : 'step-success' };
                        break;
                    case 'finish':
                        replayRunning.value = false;
                        status.value = data.success ? 'Replay finished successfully' : 'Replay failed at step ' + (data.stopped_at + 1);
                        if (replayWs) { replayWs.close(); replayWs = null; }
                        break;
                    case 'error':
                        replayRunning.value = false;
                        status.value = 'Replay error: ' + data.message;
                        break;
                }
            };
            replayWs.onclose = () => { replayRunning.value = false; replayWs = null; };
            replayWs.onerror = () => { status.value = 'Replay WebSocket error'; replayRunning.value = false; };
        };

        const stopReplay = () => {
            if (replayWs) { replayWs.close(); replayWs = null; }
            replayRunning.value = false;
            status.value = 'Replay stopped';
        };

        const exportScenario = async () => {
            const sc = currentScenario.value;
            if (!sc) return alert('Сначала выберите сценарий');
            const data = await apiPost('/scenario/export', { scenario_id: sc.id });
            if (data.status === 'ok') {
                const blob = new Blob([data.json], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = (sc.name || 'scenario') + '.json';
                a.click();
                URL.revokeObjectURL(url);
            }
        };

        const importScenario = async () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json,application/json';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const text = await file.text();
                let obj;
                try { obj = JSON.parse(text); } catch (err) { alert('Invalid JSON'); return; }
                const data = await apiPost('/scenario/import', { name: obj.name || file.name.replace(/\.json$/i, ''), steps: obj.steps || [] });
                if (data.status === 'ok') {
                    scenarios.value.push(data.scenario);
                    currentScenarioId.value = data.scenario.id;
                }
            };
            input.click();
        };

        // Agent
        const startAgent = (cfg) => {
            if (ws) ws.close();
            agentRunning.value = true;
            const logEl = document.querySelector('.reasoning-log');
            if (logEl) logEl.innerHTML = '';
            ws = new WebSocket('ws://' + location.host + '/ws/agent');
            ws.onopen = () => {
                ws.send(JSON.stringify({
                    task: cfg.task, url: url.value, text_mode: cfg.textMode,
                    provider: cfg.provider, max_steps: cfg.maxSteps,
                    headless: false, screenshot_on_demand: true
                }));
            };
            ws.onmessage = (e) => handleAgentEvent(JSON.parse(e.data));
            ws.onclose = () => { agentRunning.value = false; ws = null; };
            ws.onerror = () => { agentRunning.value = false; };
        };

        const stopAgent = () => {
            if (ws) { ws.close(); ws = null; }
            agentRunning.value = false;
        };

        const takeStepScreenshot = async () => {
            const res = await apiPost('/agent_screenshot', {});
            if (res.image) {
                setScreenshot('data:image/jpeg;base64,' + res.image);
                status.value = 'Скриншот шага: ' + new Date().toLocaleTimeString();
            } else {
                status.value = 'Не удалось получить скриншот: ' + (res.message || '');
            }
        };

        let currentStepCard = null;
        const handleAgentEvent = (data) => {
            switch (data.type) {
                case 'screenshot':
                    setScreenshot('data:image/jpeg;base64,' + data.base64);
                    status.value = 'Шаг ' + (data.step || '') + ' обновлён: ' + new Date().toLocaleTimeString();
                    break;
                case 'snapshot_text':
                    status.value = 'Step snapshot: ' + data.elements_count + ' elements @ ' + (data.url || '');
                    break;
                case 'step_start':
                    currentStepCard = { step: data.step, max_steps: data.max_steps };
                    break;
                case 'llm_decision':
                    if (currentStepCard) {
                        currentStepCard.action_type = data.action_type;
                        currentStepCard.reasoning = data.reasoning;
                        currentStepCard.fallback = data.fallback;
                    } else {
                        currentStepCard = { action_type: data.action_type, reasoning: data.reasoning, fallback: data.fallback };
                    }
                    break;
                case 'action_result':
                    if (currentStepCard) {
                        currentStepCard.observation = data.observation;
                        currentStepCard.fallback = currentStepCard.fallback || data.fallback;
                        flushStepCard();
                        currentStepCard = null;
                    }
                    break;
                case 'error':
                    appendStepCard({ title: 'Ошибка', error: data.message, cls: 'error' });
                    break;
                case 'finish':
                    appendStepCard({ title: data.success ? '✓ Завершено' : '✗ Неудача', result: data.summary || '', cls: data.success ? 'finish-success' : 'finish-fail' });
                    agentRunning.value = false;
                    break;
            }
        };

        const flushStepCard = () => {
            if (!currentStepCard) return;
            const step = currentStepCard.step || '';
            const max = currentStepCard.max_steps || '';
            const fallback = currentStepCard.fallback ? ' (vision fallback)' : '';
            const title = step ? `Step ${step}/${max} — ${(currentStepCard.action_type || '').toUpperCase()}${fallback}` : (currentStepCard.action_type || '').toUpperCase();
            appendStepCard({ title, reason: currentStepCard.reasoning || '', result: currentStepCard.observation || '' });
        };

        const appendStepCard = ({ title, reason, result, error, cls }) => {
            const log = document.querySelector('.reasoning-log');
            if (!log) return;
            const card = document.createElement('div');
            card.className = 'step-card ' + (cls || '');
            let html = `<div class="step-title">${escapeHtml(title)}</div>`;
            if (reason) html += `<div class="step-reason">${escapeHtml(reason)}</div>`;
            if (result) html += `<div class="step-result">${escapeHtml(result)}</div>`;
            if (error) html += `<div class="step-error">${escapeHtml(error)}</div>`;
            card.innerHTML = html;
            log.appendChild(card);
            log.scrollTop = log.scrollHeight;
        };

        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };

        onMounted(async () => {
            await refreshScreenshot();
            startAutoRefresh();
            await loadScenarios();
        });

        return {
            url, screenshot, elements, status, activeTab,
            scenarios, currentScenarioId, currentScenario,
            autoRecordEnabled, replayDelay, replayRunning, stepHighlights,
            modalVisible, modalEditIndex, modalInitial,
            agentRunning,
            navigate, sendAction, takeScreenshot, typeText, refreshScreenshot, switchTab,
            createScenario, selectScenario, renameScenario, deleteScenario,
            toggleAutoRecord, recordLastAction, moveStep, duplicateStep, deleteStep,
            formatStepInfo, openModal, closeModal, saveModal,
            startReplay, stopReplay, exportScenario, importScenario,
            startAgent, stopAgent, takeStepScreenshot,
            escapeHtml
        };
    },
    template: `
        <div class="container">
            <h1>SkreenMaker — Interactive Browser TUI</h1>
            <div class="toolbar">
                <input type="text" v-model="url" placeholder="https://example.com">
                <button @click="navigate">Перейти</button>
                <button class="secondary" @click="refreshScreenshot">Обновить скрин</button>
                <button class="secondary" @click="takeScreenshot">Скриншот</button>
            </div>

            <div class="main">
                <div class="panel screenshot-wrap">
                    <img :src="screenshot" alt="Annotated screenshot">
                    <div class="status">{{ status }}</div>
                </div>

                <div>
                    <div class="tabs">
                        <div class="tab" :class="{active: activeTab==='manual'}" @click="switchTab('manual')">Manual</div>
                        <div class="tab" :class="{active: activeTab==='agent'}" @click="switchTab('agent')">Агент</div>
                    </div>

                    <div v-show="activeTab==='manual'" class="tab-content active">
                        <div class="panel">
                            <div class="section-title">Элементы</div>
                            <div class="elements-grid">
                                <button class="el-btn" v-for="(info, id) in elements" :key="id" @click="sendAction({action_type:'click', element_display_id: parseInt(id)})">
                                    <span class="num">{{ id }}</span>{{ info.tag }}: {{ info.text || '' }}
                                </button>
                            </div>

                            <div class="section-title">Быстрые действия</div>
                            <div class="quick-btns">
                                <button @click="sendAction({action_type:'press_key', key:'Enter'})">Enter</button>
                                <button @click="sendAction({action_type:'press_key', key:'Escape'})">Escape</button>
                                <button @click="sendAction({action_type:'press_key', key:'Tab'})">Tab</button>
                                <button @click="sendAction({action_type:'scroll', direction:'down'})">↓ Вниз</button>
                                <button @click="sendAction({action_type:'scroll', direction:'up'})">↑ Вверх</button>
                                <button @click="sendAction({action_type:'scroll', direction:'left'})">← Влево</button>
                                <button @click="sendAction({action_type:'scroll', direction:'right'})">→ Вправо</button>
                            </div>

                            <div class="section-title">Ввод текста</div>
                            <div class="type-box">
                                <input type="text" id="typeInput" placeholder="Текст...">
                                <button @click="typeText">Ввести</button>
                            </div>
                            <div style="font-size:12px;color:#666;margin-top:4px;">Сначала кликните по полю ввода в списке элементов, потом нажмите "Ввести"</div>
                        </div>

                        <div class="panel" style="margin-top:12px;">
                            <div class="section-title">Сценарии</div>
                            <div class="scenario-list">
                                <div class="empty-steps" v-if="scenarios.length===0">Нет сценариев</div>
                                <div class="scenario-card" v-for="s in scenarios" :key="s.id" :class="{active: s.id===currentScenarioId}" @click="selectScenario(s.id)">
                                    <div class="scenario-name">{{ s.name }}</div>
                                    <div class="scenario-meta">{{ s.steps.length }} шагов</div>
                                </div>
                            </div>
                            <div class="scenario-toolbar">
                                <button @click="createScenario">+ New</button>
                                <button class="secondary" @click="renameScenario">Rename</button>
                                <button class="danger" @click="deleteScenario">Del</button>
                            </div>
                            <div class="section-title">{{ currentScenario ? 'Шаги: ' + currentScenario.name : 'Шаги' }}</div>
                            <div class="step-list">
                                <div class="empty-steps" v-if="!currentScenario || currentScenario.steps.length===0">Нет шагов</div>
                                <div v-for="(step, idx) in (currentScenario ? currentScenario.steps : [])" :key="idx" :id="'step-row-'+idx" class="step-row" :class="stepHighlights[idx]">
                                    <div class="step-index">{{ idx + 1 }}</div>
                                    <div class="step-info">{{ formatStepInfo(step) }}</div>
                                    <div class="step-actions">
                                        <button @click="moveStep(idx, -1)" :disabled="idx===0">↑</button>
                                        <button @click="moveStep(idx, 1)" :disabled="idx===currentScenario.steps.length-1">↓</button>
                                        <button @click="duplicateStep(idx)">⧉</button>
                                        <button @click="openModal(idx, step)">✎</button>
                                        <button @click="deleteStep(idx)" style="background:#dc3545;color:#fff;">×</button>
                                    </div>
                                </div>
                            </div>
                            <div class="record-bar">
                                <button class="secondary" @click="recordLastAction" :disabled="!lastManualAction || !currentScenarioId">⏺ Record last</button>
                                <button class="secondary" @click="toggleAutoRecord" :disabled="!currentScenarioId" :class="{recording: autoRecordEnabled}">{{ autoRecordEnabled ? '⏹ Стоп' : '⏺ Запись' }}</button>
                                <button class="secondary" @click="openModal(null, null)">+ Add step</button>
                                <button v-if="!replayRunning" @click="startReplay">▶ Replay</button>
                                <button v-else class="stop" @click="stopReplay">⏹ Стоп</button>
                                <button class="secondary" @click="exportScenario">Export</button>
                                <button class="secondary" @click="importScenario">Import</button>
                            </div>
                            <div style="margin-top:8px; display:flex; align-items:center; gap:8px; font-size:12px;">
                                <label>Delay between steps:</label>
                                <input type="number" v-model.number="replayDelay" min="0" step="0.1" style="width:60px; padding:4px;"> s
                            </div>
                        </div>
                    </div>

                    <div v-show="activeTab==='agent'" class="tab-content active">
                        <agent-panel :running="agentRunning" @start="startAgent" @stop="stopAgent" @screenshot="takeStepScreenshot"></agent-panel>
                    </div>
                </div>
            </div>
        </div>
        <step-modal :visible="modalVisible" :edit-index="modalEditIndex" :initial="modalInitial" @close="closeModal" @save="saveModal"></step-modal>
    `
}).mount('#app');
