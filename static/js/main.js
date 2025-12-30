async function loadEmails() {
    const tbody = document.getElementById('emails-table');
    try {
        const res = await fetch('/api/v1/emails');
        const data = await res.json();

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5">
                        <div class="empty-state">
                            <div class="empty-icon">🚀</div>
                            <h3>Ready for takeoff?</h3>
                            <p>You haven't sent any emails yet. Use the SDK to send your first one!</p>
                            
                            <div class="code-snippet-mini">
                                <span style="color:#c084fc">import</span> { RelayMail } <span style="color:#c084fc">from</span> 'relaymail';<br>
                                <span style="color:#52525b">// start sending...</span>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.map(email => `
            <tr>
                <td><span class="badge badge-${email.status}">${email.status}</span></td>
                <td>${email.recipient}</td>
                <td><span style="font-weight:500; color:#fff">${email.subject}</span></td>
                <td class="code" style="font-size:0.85rem">${email.key_name || 'Unknown'}</td>
                <td style="color:#a1a1aa">${new Date(email.timestamp).toLocaleString()}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" style="color:#ef4444; text-align:center; padding: 20px;">Failed to load data. API might be unreachable.</td></tr>';
    }
}

async function loadMetrics() {
    try {
        const res = await fetch('/api/v1/metrics');
        const data = await res.json();

        document.getElementById('metric-total').textContent = data.total;
        document.getElementById('metric-sent').textContent = data.sent;
        document.getElementById('metric-failed').textContent = data.failed;
        document.getElementById('metric-rate').textContent = data.rate + '%';
    } catch (e) {
        console.error("Error loading metrics", e);
    }
}

async function loadKeys() {
    const container = document.getElementById('keys-list');
    try {
        const res = await fetch('/api/v1/keys');
        const data = await res.json();

        if (data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon" style="font-size: 0; margin-bottom: 32px;">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="animation: float 3s infinite ease-in-out;">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                    </div>
                    <h3>No API Keys Found</h3>
                    <p>Create a key to start sending emails via the SDK.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = data.map(key => `
            <div class="key-item">
                <div class="key-info-group">
                    <div class="key-icon-wrapper">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
                        </svg>
                    </div>
                    <div class="key-details">
                        <h3>${key.name}</h3>
                        <div class="key-mask">${key.key_token}</div>
                    </div>
                </div>
                
                <div class="key-meta">
                    <div>Created ${key.created_at ? new Date(key.created_at).toLocaleDateString() : 'Just now'}</div>
                    <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 4px;">
                        ${key.last_used ? 'Last used ' + new Date(key.last_used).toLocaleString() : 'Never used'}
                    </div>
                </div>

                <div>
                    <button class="btn-danger-ghost" onclick="openRevokeModal('${key.id}')">Revoke</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
        container.innerHTML = '<div style="color:#ef4444; text-align:center;">Failed to load API keys</div>';
    }
}

// --- Modal Logic ---
function openCreateModal() {
    document.getElementById('create-modal').classList.add('active');
    document.getElementById('key-name-input').value = '';
    document.getElementById('key-name-input').focus();
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

async function submitCreateKey() {
    const nameInput = document.getElementById('key-name-input');
    const name = nameInput.value.trim() || "My API Key";

    try {
        const res = await fetch('/api/v1/keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        if (res.ok) {
            const data = await res.json();
            closeModal('create-modal');

            // Show Success Modal
            document.getElementById('generated-key-display').textContent = data.key;
            document.getElementById('success-modal').classList.add('active');

            loadKeys(); // Refresh list
        } else {
            alert("Failed to create key");
        }
    } catch (e) {
        alert("Error creating key");
    }
}

function copyKey() {
    const key = document.getElementById('generated-key-display').textContent;
    navigator.clipboard.writeText(key).then(() => {
        const btn = document.querySelector('.copy-field button');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = originalText, 2000);
    });
}

let keyToRevoke = null;

function openRevokeModal(id) {
    keyToRevoke = id;
    document.getElementById('revoke-modal').classList.add('active');
}

async function confirmRevoke() {
    if (!keyToRevoke) return;

    try {
        await fetch(`/api/v1/keys/${keyToRevoke}`, { method: 'DELETE' });
        closeModal('revoke-modal');
        keyToRevoke = null;
        loadKeys();
    } catch (e) {
        alert("Error revoking key");
    }
}
// Old revokeKey function replaced by openRevokeModal usage in HTML

// --- Logout Logic ---
function openLogoutModal() {
    document.getElementById('logout-modal').classList.add('active');
}

function confirmLogout() {
    window.location.href = "/logout";
}

