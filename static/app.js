import { createApp, ref, computed, onMounted, watch, nextTick } from 'vue';
import { VueFlow, useVueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { MiniMap } from '@vue-flow/minimap';

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
        const task = ref('Войти в систему используя email user@example.invalid и пароль your_password_here, затем открыть раздел База знаний');
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

const FlowPanel = {
    components: { VueFlow, Background, Controls, MiniMap },
    props: ['scenarios', 'sequences', 'currentSequenceId', 'sequenceReplayDelay', 'sequenceInterDelay', 'sequenceReplayRunning'],
    emits: ['add-scenario', 'remove-scenario', 'move-scenario', 'replay', 'stop-replay', 'select-sequence', 'create-sequence', 'rename-sequence', 'delete-sequence', 'edit-scenario'],
    setup(props, { emit }) {
        const { fitView } = useVueFlow();
        const elements = ref([]);
        const panelRef = ref(null);
        const edgeTypes = {};

        const currentSequence = computed(() => props.sequences.find(q => q.id === props.currentSequenceId) || null);

        function cleanMarkers() {
            setTimeout(() => {
                document.querySelectorAll('.vue-flow__edge-path').forEach(el => {
                    el.removeAttribute('marker-end');
                    el.removeAttribute('marker-start');
                });
            }, 100);
        }

        function rebuildElements() {
            const seq = currentSequence.value;
            if (!seq) { elements.value = []; cleanMarkers(); return; }
            const ids = seq.scenario_ids || [];
            const existingPositions = {};
            elements.value.forEach(el => {
                if (!el.source && el.position) existingPositions[el.id] = { ...el.position };
            });
            const nodes = ids.map((sid, i) => {
                const s = props.scenarios.find(x => x.id === sid);
                const pos = existingPositions[sid] || { x: i * 240, y: 120 };
                return {
                    id: sid,
                    type: 'scenario',
                    position: pos,
                    data: { name: s?.name || '(deleted)', tags: s?.tags || [], group: s?.group, steps: s?.steps?.length || 0 }
                };
            });
            const edges = [];
            for (let i = 0; i < ids.length - 1; i++) {
                edges.push({
                    id: `e-${ids[i]}-${ids[i+1]}`,
                    source: ids[i],
                    target: ids[i+1],
                    type: 'default'
                });
            }
            elements.value = [...nodes, ...edges];
            cleanMarkers();
        }

        watch(() => props.currentSequenceId, () => { rebuildElements(); setTimeout(() => fitView({ padding: 0.2 }), 100); }, { immediate: true });
        watch(() => props.sequences, rebuildElements, { deep: true });
        watch(() => props.scenarios, rebuildElements, { deep: true });

        const onNodeDragStop = (_event, node) => {
            // Сортируем scenario_ids по x-координате ноды
            const seq = currentSequence.value;
            if (!seq) return;
            const ids = [...seq.scenario_ids];
            const positions = {};
            elements.value.forEach(el => {
                if (!el.source) positions[el.id] = el.position?.x ?? 0;
            });
            ids.sort((a, b) => (positions[a] || 0) - (positions[b] || 0));
            emit('reorder-sequence', ids);
        };

        const onDrop = (event) => {
            event.preventDefault();
            const sid = event.dataTransfer.getData('application/scenario-id');
            if (sid) emit('add-scenario', sid);
        };

        const onDragOver = (event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
        };

        onMounted(() => {
            cleanMarkers();
            setTimeout(() => fitView({ padding: 0.2 }), 200);
            if (panelRef.value && typeof ResizeObserver !== 'undefined') {
                const ro = new ResizeObserver(() => fitView({ padding: 0.2 }));
                ro.observe(panelRef.value);
            }
            if (panelRef.value && typeof ResizeObserver !== 'undefined') {
                // ResizeObserver disabled
                ro.observe(panelRef.value);
            }
        });

        return {
            elements, currentSequence, panelRef,
            onNodeDragStop, onDrop, onDragOver
        };
    },
    template: `
        <div class="flow-panel" ref="panelRef">
            <div class="flow-sidebar">
                <div class="section-title">Последовательности</div>
                <div class="scenario-list seq-list">
                    <div class="empty-steps" v-if="sequences.length===0">Нет последовательностей</div>
                    <div class="scenario-card" v-for="q in sequences" :key="q.id" :class="{active: q.id===currentSequenceId}" @click="$emit('select-sequence', q.id)">
                        <div class="scenario-name">{{ q.name }}</div>
                        <div class="scenario-meta">{{ (q.scenario_ids || []).length }} сценариев</div>
                    </div>
                </div>
                <div class="scenario-toolbar" style="margin-bottom:12px;">
                    <button @click="$emit('create-sequence')">+ New Seq</button>
                    <button class="secondary" @click="$emit('rename-sequence')">Rename</button>
                    <button class="danger" @click="$emit('delete-sequence')">Del</button>
                </div>


                <div v-if="currentSequence" style="margin-top:10px; border-top:1px solid #eee; padding-top:10px;">
                    <div class="record-bar">
                        <button v-if="!sequenceReplayRunning" @click="$emit('replay')">▶ Replay Seq</button>
                        <button v-else class="stop" @click="$emit('stop-replay')">⏹ Стоп</button>
                    </div>
                    <div style="margin-top:8px; display:flex; align-items:center; gap:8px; font-size:12px; flex-wrap:wrap;">
                        <label>Step delay:</label>
                        <input type="number" :value="sequenceReplayDelay" @change="$emit('update:sequenceReplayDelay', parseFloat($event.target.value)||0)" min="0" step="0.1" style="width:60px; padding:4px;"> s
                        <label>Between:</label>
                        <input type="number" :value="sequenceInterDelay" @change="$emit('update:sequenceInterDelay', parseFloat($event.target.value)||0)" min="0" step="0.1" style="width:60px; padding:4px;"> s
                    </div>
                </div>
            </div>

            <div class="flow-canvas" @drop="onDrop" @dragover="onDragOver">
                <VueFlow v-model="elements" @node-drag-stop="onNodeDragStop">
                    <template #node-scenario="nodeProps">
                        <div class="scenario-node" @dblclick="$emit('edit-scenario', nodeProps.id)">
                            <div class="node-name">{{ nodeProps.data.name }}</div>
                            <div class="node-meta">{{ nodeProps.data.steps }} шагов</div>
                            <div class="node-group" v-if="nodeProps.data.group">{{ nodeProps.data.group }}</div>
                            <div class="node-tags" v-if="nodeProps.data.tags.length">
                                <span v-for="t in nodeProps.data.tags" :key="t">{{ t }}</span>
                            </div>
                            <div class="node-actions">
                                <button @click.stop="$emit('move-scenario', nodeProps.id, -1)">↑</button>
                                <button @click.stop="$emit('move-scenario', nodeProps.id, 1)">↓</button>
                                <button class="danger" @click.stop="$emit('remove-scenario', nodeProps.id)">×</button>
                            </div>
                        </div>
                    </template>
                    <Background pattern-color="#aaa" gap="16" />
                    <Controls />
                    <MiniMap />

                </VueFlow>
            </div>
        </div>
    `
};

createApp({
    components: { AgentPanel, StepModal, FlowPanel },
    setup() {
        const url = ref('https://example.test/');
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

        // Sequence state
        const sequences = ref([]);
        const currentSequenceId = ref(null);
        const sequenceReplayDelay = ref(0.5);
        const sequenceInterDelay = ref(1.0);
        const sequenceReplayRunning = ref(false);
        let seqReplayWs = null;

        // Agent state
        const agentRunning = ref(false);
        let ws = null;
        let replayWs = null;

        const currentScenario = computed(() => scenarios.value.find(s => s.id === currentScenarioId.value) || null);
        const currentSequence = computed(() => sequences.value.find(q => q.id === currentSequenceId.value) || null);
        const allTags = computed(() => {
            const set = new Set();
            scenarios.value.forEach(s => (s.tags || []).forEach(t => set.add(t)));
            return Array.from(set).sort();
        });

        const scenarioSearch = ref('');
        const scenarioTag = ref('');
        const filteredScenarios = computed(() => {
            let list = scenarios.value;
            const q = scenarioSearch.value.trim().toLowerCase();
            if (q) list = list.filter(s => s.name.toLowerCase().includes(q) || (s.group || '').toLowerCase().includes(q));
            const t = scenarioTag.value;
            if (t) list = list.filter(s => (s.tags || []).includes(t));
            return list;
        });

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

        const setErrorScreenshot = (message) => {
            const canvas = document.createElement('canvas');
            canvas.width = 640;
            canvas.height = 360;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#f5f5f5';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#c00';
            ctx.font = 'bold 18px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('⚠ Ошибка загрузки скриншота', canvas.width / 2, 160);
            ctx.fillStyle = '#333';
            ctx.font = '14px sans-serif';
            ctx.fillText(message, canvas.width / 2, 190);
            screenshot.value = canvas.toDataURL('image/png');
        };

        const refreshScreenshot = async () => {
            try {
                const res = await apiPost('/screenshot_annotated', {});
                if (!res.image) {
                    throw new Error('Сервер вернул пустое изображение');
                }
                setScreenshot('data:image/jpeg;base64,' + res.image);
                elements.value = res.elements || {};
                status.value = '✅ Обновлено: ' + new Date().toLocaleTimeString();
            } catch (e) {
                console.error('screenshot error', e);
                setErrorScreenshot(e.message || 'Не удалось получить скриншот');
                status.value = '❌ Ошибка скриншота: ' + (e.message || 'unknown');
            }
        };

        const navigate = async () => {
            try {
                await apiPost('/navigate', { url: url.value });
                status.value = '⏳ Загрузка страницы…';
                await refreshScreenshot();
                lastManualAction.value = { action_type: 'navigate', url: url.value };
                await maybeAutoRecord();
            } catch (e) {
                console.error('navigate error', e);
                status.value = '❌ Ошибка перехода: ' + (e.message || 'unknown');
                setErrorScreenshot('Ошибка навигации: ' + (e.message || 'unknown'));
            }
        };

        const enrichAction = (action) => {
            // Ручной клик использует element_display_id напрямую (координаты).
            // Fallback-поля (selector/stable_hash) не добавляем, чтобы сервер
            // использовал click_by_coords вместо locator chain.
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

        // Tags & Groups
        const addTag = async (scenario, tag) => {
            tag = (tag || '').trim().toLowerCase();
            if (!tag) return;
            const data = await apiPost('/scenario/tag/add', { scenario_id: scenario.id, tag });
            if (data.status === 'ok') scenario.tags = data.scenario.tags || [];
        };

        const removeTag = async (scenario, tag) => {
            const data = await apiPost('/scenario/tag/remove', { scenario_id: scenario.id, tag });
            if (data.status === 'ok') scenario.tags = data.scenario.tags || [];
        };

        const setGroup = async (scenario, group) => {
            group = (group || '').trim() || null;
            const data = await apiPost('/scenario/group/set', { scenario_id: scenario.id, group });
            if (data.status === 'ok') scenario.group = data.scenario.group;
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

        // Sequences
        const loadSequences = async () => {
            const data = await apiGet('/sequence/list');
            if (data.status === 'ok') {
                sequences.value = data.sequences || [];
                currentSequenceId.value = data.current_sequence_id || null;
            }
        };

        const createSequence = async () => {
            const name = prompt('Название последовательности:', 'New sequence');
            if (!name) return;
            const data = await apiPost('/sequence/create', { name });
            if (data.status === 'ok') {
                sequences.value.push(data.sequence);
                currentSequenceId.value = data.sequence.id;
            }
        };

        const renameSequence = async () => {
            const seq = currentSequence.value;
            if (!seq) return alert('Сначала выберите последовательность');
            const name = prompt('Новое название:', seq.name);
            if (!name) return;
            const data = await apiPost('/sequence/rename', { sequence_id: seq.id, name });
            if (data.status === 'ok') seq.name = name;
        };

        const deleteSequence = async () => {
            const seq = currentSequence.value;
            if (!seq) return;
            if (!confirm(`Удалить последовательность "${seq.name}"?`)) return;
            const data = await apiPost('/sequence/delete', { sequence_id: seq.id });
            if (data.status === 'ok') {
                sequences.value = sequences.value.filter(q => q.id !== seq.id);
                currentSequenceId.value = data.current_sequence_id;
            }
        };

        const selectSequence = async (id) => {
            if (!id) return;
            await apiPost('/sequence/select', { sequence_id: id });
            currentSequenceId.value = id;
        };

        const addScenarioToSequence = async (scenarioId) => {
            const seq = currentSequence.value;
            if (!seq) return;
            const data = await apiPost('/sequence/add_scenario', { sequence_id: seq.id, scenario_ids: [scenarioId] });
            if (data.status === 'ok') seq.scenario_ids = data.sequence.scenario_ids;
        };

        const removeScenarioFromSequence = async (scenarioId) => {
            const seq = currentSequence.value;
            if (!seq) return;
            const data = await apiPost('/sequence/remove_scenario', { sequence_id: seq.id, scenario_ids: [scenarioId] });
            if (data.status === 'ok') seq.scenario_ids = data.sequence.scenario_ids;
        };

        const reorderSequence = async (ids) => {
            const seq = currentSequence.value;
            if (!seq) return;
            const data = await apiPost('/sequence/reorder', { sequence_id: seq.id, scenario_ids: ids });
            if (data.status === 'ok') seq.scenario_ids = data.sequence.scenario_ids;
        };

        const startSequenceReplay = () => {
            const seq = currentSequence.value;
            if (!seq || !seq.scenario_ids || seq.scenario_ids.length === 0) return alert('Нет сценариев в последовательности');
            if (seqReplayWs) seqReplayWs.close();
            clearHighlights();
            sequenceReplayRunning.value = true;
            status.value = 'Sequence replay running...';
            seqReplayWs = new WebSocket('ws://' + location.host + '/ws/replay_sequence');
            seqReplayWs.onopen = () => {
                seqReplayWs.send(JSON.stringify({
                    sequence_id: seq.id,
                    delay: parseFloat(sequenceReplayDelay.value) || 0,
                    inter_scenario_delay: parseFloat(sequenceInterDelay.value) || 0
                }));
            };
            seqReplayWs.onmessage = (e) => {
                const data = JSON.parse(e.data);
                switch (data.type) {
                    case 'scenario_start':
                        status.value = `Sequence: ${data.name || '(deleted)'} [${data.scenario_index + 1}/${seq.scenario_ids.length}]`;
                        break;
                    case 'step_start': break;
                    case 'screenshot':
                        if (data.image) {
                            setScreenshot('data:image/jpeg;base64,' + data.image);
                            if (data.elements) elements.value = data.elements;
                        }
                        break;
                    case 'scenario_result':
                        if (!data.success && !data.skipped) {
                            status.value = `Sequence failed in scenario ${data.scenario_id}`;
                        }
                        break;
                    case 'finish':
                        sequenceReplayRunning.value = false;
                        status.value = data.success ? 'Sequence replay finished successfully' : 'Sequence replay finished with errors';
                        if (seqReplayWs) { seqReplayWs.close(); seqReplayWs = null; }
                        break;
                    case 'error':
                        sequenceReplayRunning.value = false;
                        status.value = 'Sequence replay error: ' + data.message;
                        break;
                }
            };
            seqReplayWs.onclose = () => { sequenceReplayRunning.value = false; seqReplayWs = null; };
            seqReplayWs.onerror = () => { status.value = 'Sequence replay WebSocket error'; sequenceReplayRunning.value = false; };
        };

        const stopSequenceReplay = () => {
            if (seqReplayWs) { seqReplayWs.close(); seqReplayWs = null; }
            sequenceReplayRunning.value = false;
            status.value = 'Sequence replay stopped';
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
            try { await refreshScreenshot(); } catch (e) { console.error('screenshot error', e); }
            startAutoRefresh();
            await loadScenarios();
            await loadSequences();
        });

        return {
            url, screenshot, elements, status, activeTab,
            scenarios, currentScenarioId, currentScenario,
            sequences, currentSequenceId, currentSequence,
            sequenceReplayDelay, sequenceInterDelay, sequenceReplayRunning,
            allTags, scenarioSearch, scenarioTag, filteredScenarios,
            autoRecordEnabled, replayDelay, replayRunning, stepHighlights,
            modalVisible, modalEditIndex, modalInitial,
            agentRunning, lastManualAction,
            navigate, sendAction, takeScreenshot, typeText, refreshScreenshot, switchTab,
            createScenario, selectScenario, renameScenario, deleteScenario,
            addTag, removeTag, setGroup,
            toggleAutoRecord, recordLastAction, moveStep, duplicateStep, deleteStep,
            formatStepInfo, openModal, closeModal, saveModal,
            startReplay, stopReplay, exportScenario, importScenario,
            createSequence, selectSequence, renameSequence, deleteSequence,
            addScenarioToSequence, removeScenarioFromSequence, reorderSequence,
            startSequenceReplay, stopSequenceReplay,
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
                <div class="main-inner-grid">
                    <div class="left-col">
                        <div class="panel screenshot-wrap">
                            <img :src="screenshot" alt="Annotated screenshot">
                            <div class="status">{{ status }}</div>
                        </div>
                        <div class="panel steps-panel">
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
                        <div class="panel flow-panel-wrap">
                            <flow-panel
                                :scenarios="scenarios"
                                :sequences="sequences"
                                :current-sequence-id="currentSequenceId"
                                :sequence-replay-delay="sequenceReplayDelay"
                                :sequence-inter-delay="sequenceInterDelay"
                                :sequence-replay-running="sequenceReplayRunning"

                                @select-sequence="selectSequence"
                                @create-sequence="createSequence"
                                @rename-sequence="renameSequence"
                                @delete-sequence="deleteSequence"
                                @add-scenario="addScenarioToSequence"
                                @remove-scenario="removeScenarioFromSequence"
                                @move-scenario="(sid, dir) => { const seq = currentSequence; if (!seq) return; const idx = seq.scenario_ids.indexOf(sid); if (idx >= 0) moveSeqScenario(idx, dir); }"
                                @reorder-sequence="reorderSequence"
                                @replay="startSequenceReplay"
                                @stop-replay="stopSequenceReplay"
                                @edit-scenario="(sid) => { selectScenario(sid); switchTab('manual'); }"
                            ></flow-panel>
                        </div>
                    </div>
                    <div class="right-col">
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
                            <div class="panel scenarios-panel">
                                <div class="section-title">Сценарии</div>
                                <input type="text" v-model="scenarioSearch" placeholder="Поиск..." style="width:100%;padding:6px;margin-bottom:6px;font-size:12px;">
                                <select v-model="scenarioTag" style="width:100%;padding:6px;margin-bottom:8px;font-size:12px;">
                                    <option value="">Все теги</option>
                                    <option v-for="t in allTags" :key="t" :value="t">{{ t }}</option>
                                </select>
                                <div class="scenario-list">
                                    <div class="empty-steps" v-if="filteredScenarios.length===0">Нет сценариев</div>
                                    <div class="scenario-card" v-for="s in filteredScenarios" :key="s.id" :class="{active: s.id===currentScenarioId}" @click="selectScenario(s.id)">
                                        <div class="scenario-name">{{ s.name }}</div>
                                        <div class="scenario-meta">{{ s.steps.length }} шагов <span v-if="s.group" class="group-label">{{ s.group }}</span> <button class="secondary" style="font-size:11px;padding:2px 6px;margin-left:6px;" @click.stop="addScenarioToSequence(s.id)" :disabled="!currentSequenceId">→ Seq</button></div>
                                        <div class="tag-row" v-if="(s.tags || []).length">
                                            <span class="tag-badge" v-for="t in s.tags" :key="t">{{ t }}</span>
                                        </div>
                                        <div class="scenario-edit-row" v-if="s.id===currentScenarioId" @click.stop>
                                            <input type="text" placeholder="+ tag" style="width:80px;font-size:11px;padding:4px;" @keydown.enter="addTag(s, $event.target.value); $event.target.value=''">
                                            <input type="text" placeholder="group" :value="s.group || ''" style="width:80px;font-size:11px;padding:4px;" @change="setGroup(s, $event.target.value)">
                                        </div>
                                    </div>
                                </div>
                                <div class="scenario-toolbar">
                                    <button @click="createScenario">+ New</button>
                                    <button class="secondary" @click="renameScenario">Rename</button>
                                    <button class="danger" @click="deleteScenario">Del</button>
                                </div>
                            </div>
                        </div>
                        <div v-show="activeTab==='agent'" class="tab-content active">
                            <agent-panel :running="agentRunning" @start="startAgent" @stop="stopAgent" @screenshot="takeStepScreenshot"></agent-panel>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <step-modal :visible="modalVisible" :edit-index="modalEditIndex" :initial="modalInitial" @close="closeModal" @save="saveModal"></step-modal>
    `
}).mount('#app');
