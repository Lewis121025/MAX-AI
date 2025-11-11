// Max AI Agent Web 应用主脚本

class MaxAIApp {
    constructor() {
        this.elements = {
            chatArea: document.getElementById('chat-area'),
            chatMessages: document.getElementById('chat-messages'),
            userInput: document.getElementById('user-input'),
            btnSend: document.getElementById('btn-send'),
            btnClear: document.getElementById('btn-clear'),
            btnExport: document.getElementById('btn-export'),
            btnNewSession: document.getElementById('btn-new-session'),
            historyList: document.getElementById('history-list'),
            btnUpload: document.getElementById('btn-upload'),
            fileInput: document.getElementById('file-input'),
            filePreviewContainer: document.getElementById('file-preview-container'),
            sessionTitle: document.getElementById('session-title'),
            statusGrid: document.getElementById('status-grid'),
            examplePromptsContainer: document.getElementById('example-prompts'),
            themeButtons: {
                light: document.getElementById('btn-theme-light'),
                dark: document.getElementById('btn-theme-dark'),
            }
        };

        this.state = {
            isProcessing: false,
            currentSessionId: null,
            sessions: [],
            uploadedFiles: [],
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.applyInitialTheme();
        this.configureMarkdown();
    }

    setupEventListeners() {
        this.elements.btnSend.addEventListener('click', () => this.sendMessage());
        this.elements.btnClear.addEventListener('click', () => this.clearChat());
        this.elements.btnUpload.addEventListener('click', () => this.elements.fileInput.click());
        this.elements.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.elements.btnNewSession.addEventListener('click', () => this.createNewSession());
        this.elements.btnExport.addEventListener('click', () => this.exportChat());

        this.elements.userInput.addEventListener('input', () => this.handleInput());
        this.elements.userInput.addEventListener('keydown', (e) => this.handleKeyPress(e));

        this.elements.themeButtons.light.addEventListener('click', () => this.setTheme('light'));
        this.elements.themeButtons.dark.addEventListener('click', () => this.setTheme('dark'));
        
        document.addEventListener('click', (e) => {
            // 事件委托：处理动态元素的点击
            if (e.target.closest('.prompt-card')) {
                this.handleExamplePromptClick(e.target.closest('.prompt-card'));
            }
            if (e.target.closest('.process-header')) {
                this.toggleThinkingProcess(e.target.closest('.process-header'));
            }
            if (e.target.closest('.btn-delete-session')) {
                e.stopPropagation();
                this.deleteSession(e.target.closest('.history-item').dataset.sessionId);
            }
            if (e.target.closest('.history-item')) {
                this.loadSession(e.target.closest('.history-item').dataset.sessionId);
            }
        });
    }

    async loadInitialData() {
        await this.loadSystemStatus();
        await this.loadSessions();
    }

    applyInitialTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
    }
    
    configureMarkdown() {
        if (window.marked) {
            window.marked.setOptions({
                highlight: (code, lang) => {
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, { language }).value;
                },
                langPrefix: 'hljs language-',
            });
        }
    }

    setTheme(theme) {
        document.body.dataset.theme = theme;
        localStorage.setItem('theme', theme);
        this.elements.themeButtons.light.classList.toggle('active', theme === 'light');
        this.elements.themeButtons.dark.classList.toggle('active', theme === 'dark');
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            const statusMap = {
                'LLM': status.llm,
                '搜索': status.tools.tavily,
                '代码执行': status.tools.e2b,
                '网页抓取': status.tools.firecrawl,
                '记忆系统': status.memory,
            };
            this.elements.statusGrid.innerHTML = Object.entries(statusMap).map(([label, isActive]) => `
                <div class="status-item">
                    <span class="status-indicator ${isActive ? 'active' : 'inactive'}"></span>
                    <span class="status-label">${label}</span>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load system status:', error);
            this.elements.statusGrid.innerHTML = '<p class="error-text">无法加载系统状态</p>';
        }
    }

    async loadSessions(selectSessionId = null) {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();

            if (data.success) {
                this.state.sessions = data.sessions;
                this.renderHistory();

                const newSessionId = selectSessionId || (this.state.sessions.length > 0 ? this.state.sessions[0].id : null);
                
                if (this.state.currentSessionId !== newSessionId) {
                    this.state.currentSessionId = newSessionId;
                    if (this.state.currentSessionId) {
                        this.loadSession(this.state.currentSessionId);
                    } else {
                        this.showWelcomeScreen();
                    }
                }
            } else {
                console.error('Failed to load sessions:', data.message);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    renderHistory() {
        if (this.state.sessions.length === 0) {
            this.elements.historyList.innerHTML = '<p class="no-history">没有历史会话</p>';
            return;
        }

        this.elements.historyList.innerHTML = this.state.sessions.map(session => `
            <div class="history-item ${session.id === this.state.currentSessionId ? 'active' : ''}" data-session-id="${session.id}">
                <span class="history-title">${this.escapeHtml(session.title)}</span>
                <button class="btn-delete-session" title="删除会话"><i class="fa-solid fa-trash-can"></i></button>
            </div>
        `).join('');
    }

    async loadSession(sessionId) {
        if (!sessionId || this.state.isProcessing) return;
        
        this.state.currentSessionId = sessionId;
        this.updateActiveSessionInHistory();
        
        const session = this.state.sessions.find(s => s.id === sessionId);
        this.elements.sessionTitle.textContent = session ? session.title : '加载中...';

        try {
            const response = await fetch(`/api/session_history?session_id=${sessionId}`);
            const data = await response.json();

            this.elements.chatMessages.innerHTML = '';
            if (data.success && data.history.length > 0) {
                data.history.forEach(msg => {
                    if (msg.type === 'human') {
                        this.addUserMessage(msg.data.content);
                    } else if (msg.type === 'ai') {
                        this.addAgentMessage(msg.data.content);
                    }
                });
            } else {
                this.showWelcomeScreen();
            }
        } catch (error) {
            console.error('Failed to load session history:', error);
            this.showWelcomeScreen();
        }
    }
    
    updateActiveSessionInHistory() {
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.toggle('active', item.dataset.sessionId === this.state.currentSessionId);
        });
    }

    async createNewSession() {
        // 如果有当前会话且有消息，先保存当前会话
        if (this.state.currentSessionId) {
            const messages = this.extractMessagesFromChat();
            console.log('提取到的消息:', messages);
            console.log('当前会话ID:', this.state.currentSessionId);
            
            if (messages.length > 0) {
                try {
                    const response = await fetch('/api/save_session', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: this.state.currentSessionId,
                            messages: messages
                        })
                    });
                    const data = await response.json();
                    console.log('保存会话响应:', data);
                    
                    if (data.success) {
                        // 保存成功后重新加载会话列表，以便更新标题
                        await this.loadSessions();
                    } else {
                        console.error('保存会话失败:', data.message || data);
                    }
                } catch (error) {
                    console.error('保存会话失败:', error);
                    alert('保存会话失败: ' + error.message);
                }
            } else {
                console.log('没有消息需要保存');
            }
        } else {
            console.log('没有当前会话ID');
        }
        
        this.state.currentSessionId = null;
        this.showWelcomeScreen();
        this.elements.sessionTitle.textContent = '新会话';
        this.updateActiveSessionInHistory();
    }

    extractMessagesFromChat() {
        // 从聊天区域提取消息
        const messages = [];
        const messageElements = this.elements.chatMessages.querySelectorAll('.message');
        
        console.log('找到消息元素数量:', messageElements.length);
        
        messageElements.forEach((msgEl, index) => {
            const contentEl = msgEl.querySelector('.message-content');
            if (!contentEl) {
                console.log(`消息 ${index}: 没有找到 .message-content`);
                return;
            }
            
            // 跳过加载指示器和错误消息
            if (contentEl.querySelector('.loading-dots')) {
                console.log(`消息 ${index}: 跳过加载指示器`);
                return;
            }
            if (contentEl.querySelector('.error-message')) {
                console.log(`消息 ${index}: 跳过错误消息`);
                return;
            }
            
            let content = '';
            
            // 检查是否是最终答案
            const finalAnswerEl = contentEl.querySelector('.final-answer');
            if (finalAnswerEl) {
                const answerContent = finalAnswerEl.querySelector('.answer-content');
                if (answerContent) {
                    content = (answerContent.textContent || answerContent.innerText || '').trim();
                    console.log(`消息 ${index}: 提取最终答案，长度: ${content.length}`);
                }
            } else {
                // 普通消息
                content = contentEl.textContent || contentEl.innerText || '';
                content = content.trim();
                console.log(`消息 ${index}: 提取普通消息，长度: ${content.length}`);
            }
            
            if (!content) {
                console.log(`消息 ${index}: 内容为空，跳过`);
                return;
            }
            
            if (msgEl.classList.contains('user-message')) {
                messages.push({
                    type: 'human',
                    content: content
                });
                console.log(`消息 ${index}: 添加用户消息`);
            } else if (msgEl.classList.contains('agent-message')) {
                messages.push({
                    type: 'ai',
                    content: content
                });
                console.log(`消息 ${index}: 添加AI消息`);
            }
        });
        
        console.log('最终提取的消息数量:', messages.length);
        return messages;
    }

    async deleteSession(sessionId) {
        if (!sessionId) {
            console.error('删除会话失败: 会话ID为空');
            return;
        }
        
        if (confirm('确定要删除这个会话吗？此操作不可撤销。')) {
            try {
                console.log('正在删除会话:', sessionId);
                const response = await fetch('/api/delete_session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP ${response.status}: ${errorText}`);
                }
                
                const data = await response.json();
                console.log('删除会话响应:', data);
                
                if (data.success) {
                    // 如果删除的是当前会话，清空当前会话
                    if (this.state.currentSessionId === sessionId) {
                        this.state.currentSessionId = null;
                        this.showWelcomeScreen();
                        this.elements.sessionTitle.textContent = '新会话';
                    }
                    await this.loadSessions();
                } else {
                    alert(`删除失败: ${data.message || '未知错误'}`);
                }
            } catch (error) {
                console.error('删除会话失败:', error);
                alert(`删除会话失败: ${error.message}`);
            }
        }
    }

    handleInput() {
        const hasText = this.elements.userInput.value.trim().length > 0;
        const hasFiles = this.state.uploadedFiles.length > 0;
        this.elements.btnSend.disabled = (!hasText && !hasFiles) || this.state.isProcessing;
        this.autoResizeInput();
    }

    handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    autoResizeInput() {
        const input = this.elements.userInput;
        input.style.height = 'auto';
        input.style.height = `${Math.min(input.scrollHeight, 200)}px`;
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.state.uploadedFiles.push(...files);
        this.renderFilePreviews();
        this.handleInput();
        this.elements.fileInput.value = ''; // 允许重新选择相同的文件
    }

    renderFilePreviews() {
        if (this.state.uploadedFiles.length === 0) {
            this.elements.filePreviewContainer.innerHTML = '';
            return;
        }
        this.elements.filePreviewContainer.innerHTML = this.state.uploadedFiles.map((file, index) => `
            <div class="file-pill" data-index="${index}">
                <span>${this.escapeHtml(file.name)}</span>
                <button onclick="app.removeFile(${index})">&times;</button>
            </div>
        `).join('');
    }

    removeFile(index) {
        this.state.uploadedFiles.splice(index, 1);
        this.renderFilePreviews();
        this.handleInput();
    }

    async sendMessage() {
        const query = this.elements.userInput.value.trim();
        if ((!query && this.state.uploadedFiles.length === 0) || this.state.isProcessing) return;

        this.elements.chatMessages.querySelector('.welcome-screen')?.remove();

        let displayQuery = query;
        if (this.state.uploadedFiles.length > 0) {
            const fileNames = this.state.uploadedFiles.map(f => f.name).join(', ');
            displayQuery += `\n\n*上传的文件: ${fileNames}*`;
        }
        this.addUserMessage(displayQuery);
        
        this.elements.userInput.value = '';
        this.autoResizeInput();

        const formData = new FormData();
        formData.append('query', query);
        if (this.state.currentSessionId) {
            formData.append('session_id', this.state.currentSessionId);
        }
        this.state.uploadedFiles.forEach(file => formData.append('files', file));

        this.state.uploadedFiles = [];
        this.renderFilePreviews();
        this.setProcessingState(true);

        const agentMsgId = `msg-${Date.now()}`;
        this.addAgentMessage('', agentMsgId);
        this.addLoadingIndicator(agentMsgId);

        try {
            await this.streamResponse(formData, agentMsgId);
        } catch (error) {
            this.addErrorMessage(agentMsgId, `请求失败: ${error.message}`);
        } finally {
            this.setProcessingState(false);
            this.removeLoadingIndicator(agentMsgId);
            if (!this.state.currentSessionId) {
                // 这是一个新会话，重新加载以获取新的会话 ID 和标题
                await this.loadSessions();
            } else {
                // 仅更新历史记录列表，以防标题更改
                const response = await fetch('/api/sessions');
                const data = await response.json();
                if (data.success) {
                    this.state.sessions = data.sessions;
                    this.renderHistory();
                }
            }
        }
    }
    
    setProcessingState(isProcessing) {
        this.state.isProcessing = isProcessing;
        this.elements.btnSend.disabled = isProcessing;
        this.elements.btnSend.innerHTML = isProcessing 
            ? '<i class="fa-solid fa-spinner fa-spin"></i>' 
            : '<i class="fa-solid fa-paper-plane"></i>';
        this.handleInput();
    }

    streamResponse(formData, agentMsgId) {
        return new Promise((resolve, reject) => {
            fetch('/api/chat', { method: 'POST', body: formData })
                .then(response => {
                    if (!response.ok) {
                        // 尝试读取错误详情
                        return response.text().then(text => {
                            let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                            try {
                                const errorData = JSON.parse(text);
                                // 优先显示 detail 字段（FastAPI 标准错误格式）
                                errorMsg = errorData.detail || errorData.error || errorData.message || errorMsg;
                                // 如果是文件上传错误，直接显示详细错误信息
                                if (errorData.detail && errorData.detail.includes('无法上传')) {
                                    errorMsg = errorData.detail;
                                }
                            } catch (e) {
                                if (text) {
                                    // 尝试从文本中提取错误信息
                                    if (text.includes('detail')) {
                                        try {
                                            const match = text.match(/"detail":\s*"([^"]+)"/);
                                            if (match) errorMsg = match[1];
                                        } catch (e2) {}
                                    }
                                    if (errorMsg === `HTTP ${response.status}: ${response.statusText}`) {
                                        errorMsg += ` - ${text.substring(0, 200)}`;
                                    }
                                }
                            }
                            throw new Error(errorMsg);
                        });
                    }
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = ''; // 用于处理跨块的数据
                    const readStream = () => {
                        reader.read().then(({ done, value }) => {
                            if (done) {
                                // 处理剩余的缓冲区
                                if (buffer.trim()) {
                                    buffer.split('\n').forEach(line => {
                                        if (line.trim().startsWith('data: ')) {
                                            try {
                                                const data = JSON.parse(line.substring(6));
                                                this.handleStreamData(data, agentMsgId);
                                            } catch (e) { 
                                                console.error('Parse error:', e, 'Line:', line); 
                                            }
                                        }
                                    });
                                }
                                resolve();
                                return;
                            }
                            const text = decoder.decode(value, { stream: true });
                            buffer += text;
                            // 处理完整的行
                            const lines = buffer.split('\n');
                            buffer = lines.pop() || ''; // 保留最后不完整的行
                            
                            lines.forEach(line => {
                                if (line.trim().startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.substring(6));
                                        this.handleStreamData(data, agentMsgId);
                                    } catch (e) { 
                                        console.error('Parse error:', e, 'Line:', line); 
                                    }
                                }
                            });
                            readStream();
                        }).catch(err => {
                            console.error('Stream read error:', err);
                            this.addErrorMessage(agentMsgId, `流式响应读取失败: ${err.message}`);
                            reject(err);
                        });
                    };
                    readStream();
                }).catch(err => {
                    console.error('Fetch error:', err);
                    this.addErrorMessage(agentMsgId, `请求失败: ${err.message}`);
                    reject(err);
                });
        });
    }

    handleStreamData(data, agentMsgId) {
        const { node, data: nodeData } = data;
        
        console.log('Stream data received:', node, nodeData); // 调试信息
        
        if (node === 'session') {
            // 处理会话ID更新
            if (nodeData.session_id) {
                if (!this.state.currentSessionId) {
                    this.state.currentSessionId = nodeData.session_id;
                    console.log('会话ID已设置:', this.state.currentSessionId);
                } else if (this.state.currentSessionId !== nodeData.session_id) {
                    // 如果会话ID已存在但不同，更新它
                    this.state.currentSessionId = nodeData.session_id;
                    console.log('会话ID已更新:', this.state.currentSessionId);
                }
            }
        } else if (node === 'fast_agent') {
            // FastAgent 返回最终结果
            this.removeLoadingIndicator(agentMsgId);
            this.updateFastAgentUI(agentMsgId, nodeData);
        } else if (node === 'done') {
            // 流式响应完成，可以忽略或记录
            console.log('流式响应完成');
        } else if (node === 'error') {
            this.removeLoadingIndicator(agentMsgId);
            // 处理错误消息，可能是对象或字符串
            let errorMsg = '未知错误';
            if (typeof nodeData === 'string') {
                errorMsg = nodeData;
            } else if (nodeData) {
                // 优先显示具体的错误信息
                if (nodeData.details?.error_message) {
                    // 最具体的错误信息
                    errorMsg = nodeData.details.error_message;
                } else if (nodeData.details?.original_error) {
                    // 原始错误信息
                    errorMsg = nodeData.details.original_error;
                } else if (nodeData.message) {
                    // 用户友好的消息
                    errorMsg = nodeData.message;
                } else if (typeof nodeData.error === 'string') {
                    errorMsg = nodeData.error;
                } else if (nodeData.details) {
                    // 如果有 details，显示详细信息
                    const detailStr = JSON.stringify(nodeData.details, null, 2);
                    errorMsg = `错误详情:\n${detailStr}`;
                } else {
                    errorMsg = JSON.stringify(nodeData);
                }
            }
            console.error('API Error:', errorMsg, nodeData);
            this.addErrorMessage(agentMsgId, errorMsg);
        } else {
            // 其他节点类型，记录但不处理
            console.log('Unhandled stream node:', node, nodeData);
        }
    }

    updateFastAgentUI(agentMsgId, nodeData) {
        const agentMsg = document.getElementById(agentMsgId);
        if (!agentMsg) return;

        const content = agentMsg.querySelector('.message-content');
        
        // 显示最终答案
        const finalAnswer = nodeData.final_answer || '任务完成';
        
        content.innerHTML = `
            <div class="final-answer">
                <div class="answer-content">
                    ${this.renderMarkdown(finalAnswer)}
                </div>
            </div>
        `;
        
        this.scrollToBottom();
    }

    updateAgentMessageUI(agentMsgId, nodeName, nodeData) {
        const agentMsg = document.getElementById(agentMsgId);
        if (!agentMsg) return;

        let thinkingProcess = agentMsg.querySelector('.thinking-process');
        if (!thinkingProcess) {
            const content = agentMsg.querySelector('.message-content');
            content.innerHTML = `
                <div class="thinking-process collapsed">
                    <div class="process-header">
                        <i class="fa-solid fa-chevron-right toggle-icon"></i>
                        <span>思考过程</span>
                    </div>
                    <div class="process-steps"></div>
                </div>
                <div class="final-answer" style="display: none;"></div>
            `;
            thinkingProcess = agentMsg.querySelector('.thinking-process');
        }
        
        const processStepsContainer = thinkingProcess.querySelector('.process-steps');
        const finalAnswerContainer = agentMsg.querySelector('.final-answer');
        
        let stepEl = processStepsContainer.querySelector(`[data-node="${nodeName}"]`);
        if (!stepEl) {
            stepEl = document.createElement('div');
            stepEl.className = `process-step`;
            stepEl.dataset.node = nodeName;
            processStepsContainer.appendChild(stepEl);
        }
        stepEl.innerHTML = this.renderNodeContent(nodeName, nodeData);

        if (nodeName === 'critic' && nodeData.is_complete) {
            const finalReflection = nodeData.reflection || '任务已完成。';
            finalAnswerContainer.innerHTML = `
                <div class="answer-header">
                    <i class="fa-solid fa-sparkles"></i>
                    <span>最终结论</span>
                </div>
                <div class="answer-content">${this.renderMarkdown(finalReflection)}</div>
            `;
            finalAnswerContainer.style.display = 'block';
            thinkingProcess.classList.add('collapsed');
        } else {
            thinkingProcess.classList.remove('collapsed');
        }
        
        this.scrollToBottom();
    }

    renderNodeContent(nodeName, data) {
        const icons = { planner: 'fa-lightbulb', executor: 'fa-terminal', critic: 'fa-gavel' };
        const titles = { planner: '规划', executor: `执行: ${this.formatToolName(data.tool)}`, critic: '评估' };
        
        let content = '';
        if (nodeName === 'planner') {
            content = `<p><strong>推理:</strong> ${this.escapeHtml(data.reasoning)}</p>
                       ${data.plan.length > 0 ? `<p><strong>步骤:</strong></p><ol>${data.plan.map(s => `<li>${this.escapeHtml(s)}</li>`).join('')}</ol>` : ''}`;
        } else if (nodeName === 'executor') {
            const code = data.generated_code || data.output;
            content = `<pre><code>${this.escapeHtml(code)}</code></pre>`;
        } else if (nodeName === 'critic') {
            content = `<p>${this.escapeHtml(data.reflection)}</p>`;
        }

        return `
            <div class="node-header ${nodeName}">
                <i class="fa-solid ${icons[nodeName]}"></i>
                <span>${titles[nodeName]}</span>
            </div>
            <div class="node-content">${content}</div>
        `;
    }

    addUserMessage(message) {
        const msgHtml = `
            <div class="message user-message">
                <div class="message-body">
                    <div class="message-content">${this.renderMarkdown(message)}</div>
                </div>
                <div class="message-avatar user-avatar">
                    <i class="fa-solid fa-user"></i>
                </div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', msgHtml);
        this.scrollToBottom();
    }

    addAgentMessage(message, msgId) {
        const id = msgId || `msg-${Date.now()}`;
        const msgHtml = `
            <div class="message agent-message" id="${id}">
                <div class="message-avatar agent-avatar">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="message-body">
                    <div class="message-content">${this.renderMarkdown(message)}</div>
                </div>
            </div>
        `;
        this.elements.chatMessages.insertAdjacentHTML('beforeend', msgHtml);
        this.scrollToBottom();
    }

    addErrorMessage(agentMsgId, error) {
        // 确保 error 是字符串
        const errorText = typeof error === 'string' ? error : (error?.message || error?.error || JSON.stringify(error) || '未知错误');
        const agentMsg = document.getElementById(agentMsgId);
        if (agentMsg) {
            const content = agentMsg.querySelector('.message-content');
            content.innerHTML = `<div class="error-message"><strong>错误:</strong> ${this.escapeHtml(errorText)}</div>`;
        }
        this.scrollToBottom();
    }

    addLoadingIndicator(agentMsgId) {
        const agentMsg = document.getElementById(agentMsgId);
        if (agentMsg) {
            const content = agentMsg.querySelector('.message-content');
            content.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
        }
    }

    removeLoadingIndicator(agentMsgId) {
        document.getElementById(agentMsgId)?.querySelector('.loading-dots')?.remove();
    }

    clearChat() {
        if (confirm('确定要清空当前对话吗？')) {
            this.elements.chatMessages.innerHTML = '';
            this.showWelcomeScreen();
        }
    }

    showWelcomeScreen() {
        this.elements.chatMessages.innerHTML = `
            <div class="welcome-screen">
                <div class="logo-large"><i class="fa-solid fa-robot"></i></div>
                <h1 class="welcome-title">Max AI 助手</h1>
                <p class="welcome-subtitle">我可以帮你执行各种任务：搜索信息、运行代码、分析数据...</p>
                <div class="example-prompts" id="example-prompts">
                    <div class="prompt-card" data-query="搜索 2024 年 AI 的最新突破">
                        <p class="title">搜索最新 AI 突破</p>
                        <p class="subtitle">获取关于人工智能的最新动态</p>
                    </div>
                    <div class="prompt-card" data-query="用 Python 写一个快速排序算法">
                        <p class="title">编写一个 Python 脚本</p>
                        <p class="subtitle">生成并执行代码</p>
                    </div>
                    <div class="prompt-card" data-query="总结这篇关于量子计算的文章：https://example.com">
                        <p class="title">总结网页内容</p>
                        <p class="subtitle">提供一个 URL 进行分析</p>
                    </div>
                    <div class="prompt-card" data-query="分析我上传的 sales_data.csv 文件，找出最畅销的产品">
                        <p class="title">分析上传的数据</p>
                        <p class="subtitle">从文件中提取见解</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    handleExamplePromptClick(card) {
        const query = card.dataset.query;
        this.elements.userInput.value = query;
        this.handleInput();
        this.sendMessage();
    }

    toggleThinkingProcess(header) {
        const thinkingProcess = header.closest('.thinking-process');
        thinkingProcess.classList.toggle('collapsed');
        const icon = header.querySelector('.toggle-icon');
        icon.classList.toggle('fa-chevron-right');
        icon.classList.toggle('fa-chevron-down');
    }

    scrollToBottom() {
        this.elements.chatArea.scrollTop = this.elements.chatArea.scrollHeight;
    }

    exportChat() {
        alert('导出功能正在开发中。');
    }

    escapeHtml(str) {
        return str.replace(/[&<>"']/g, s => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[s]);
    }

    renderMarkdown(text) {
        return window.marked ? window.marked.parse(text || '') : this.escapeHtml(text);
    }

    formatToolName(name = '') {
        return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}

const app = new MaxAIApp();
// Make removeFile globally accessible for the inline onclick handler
window.app = app;
