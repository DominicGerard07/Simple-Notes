(function () {
  'use strict';

  // State
  let notes = [];
  let folders = [];
  let activeFilter = 'all'; // 'all', 'pinned', 'folder:ID', or 'tag:TagName'
  let activeFolderId = null;
  let currentEditingFolderId = null;
  let searchQuery = '';
  let sortBy = 'updated_desc';
  let isGridView = localStorage.getItem('notes_view') !== 'list';
  let currentEditingId = null;
  let selectedColor = 'default';
  let isModalPinned = false;
  let searchDebounceTimer = null;
  let isUniversalSearch = true;

  // DOM Elements
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const backupMenuBtn = document.getElementById('backupMenuBtn');
  const exportJsonBtn = document.getElementById('exportJsonBtn');
  const importFileInput = document.getElementById('importFileInput');
  const newNoteBtn = document.getElementById('newNoteBtn');
  const emptyCreateBtn = document.getElementById('emptyCreateBtn');

  const allCountEl = document.getElementById('allCount');
  const pinnedCountEl = document.getElementById('pinnedCount');
  const foldersListEl = document.getElementById('foldersList');
  const newFolderBtn = document.getElementById('newFolderBtn');
  const tagsListEl = document.getElementById('tagsList');
  const activeFilterLabel = document.getElementById('activeFilterLabel');
  const sortSelect = document.getElementById('sortSelect');
  const viewGridBtn = document.getElementById('viewGridBtn');
  const viewListBtn = document.getElementById('viewListBtn');

  const pinnedSection = document.getElementById('pinnedSection');
  const pinnedGrid = document.getElementById('pinnedGrid');
  const othersSection = document.getElementById('othersSection');
  const othersSectionTitle = document.getElementById('othersSectionTitle');
  const notesGrid = document.getElementById('notesGrid');
  const emptyState = document.getElementById('emptyState');

  // Modal Elements
  const noteModal = document.getElementById('noteModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalEditor = document.getElementById('modalEditor');
  const insertTodoBtn = document.getElementById('insertTodoBtn');
  const insertCodeBtn = document.getElementById('insertCodeBtn');
  const modalFolder = document.getElementById('modalFolder');
  const modalTags = document.getElementById('modalTags');
  const modalPinBtn = document.getElementById('modalPinBtn');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalCancelBtn = document.getElementById('modalCancelBtn');
  const modalSaveBtn = document.getElementById('modalSaveBtn');
  const modalDeleteBtn = document.getElementById('modalDeleteBtn');
  const downloadTxtBtn = document.getElementById('downloadTxtBtn');
  const wordCountEl = document.getElementById('wordCount');
  const noteDatesEl = document.getElementById('noteDates');
  const colorDots = document.querySelectorAll('.color-dot');
  const toastNotification = document.getElementById('toastNotification');

  // Folder Modal Elements
  const folderModal = document.getElementById('folderModal');
  const folderModalTitle = document.getElementById('folderModalTitle');
  const folderNameInput = document.getElementById('folderNameInput');
  const folderParentSelect = document.getElementById('folderParentSelect');
  const folderModalError = document.getElementById('folderModalError');
  const folderModalCloseBtn = document.getElementById('folderModalCloseBtn');
  const folderModalCancelBtn = document.getElementById('folderModalCancelBtn');
  const folderModalSaveBtn = document.getElementById('folderModalSaveBtn');

  const modalProgressBar = document.getElementById('modalProgressBar');
  const modalProgressFill = document.getElementById('modalProgressFill');
  const modalProgressCount = document.getElementById('modalProgressCount');
  const modalProgressPercent = document.getElementById('modalProgressPercent');
  const modalProgressFooter = document.getElementById('modalProgressFooter');

  // Auth State & Elements
  let currentUser = null;
  let pendingResetEmail = '';

  const userProfileContainer = document.getElementById('userProfileContainer');
  const userMenuBtn = document.getElementById('userMenuBtn');
  const headerUsername = document.getElementById('headerUsername');
  const userMenuDropdown = document.getElementById('userMenuDropdown');
  const dropdownUsername = document.getElementById('dropdownUsername');
  const dropdownEmail = document.getElementById('dropdownEmail');
  const logoutBtn = document.getElementById('logoutBtn');

  const authModal = document.getElementById('authModal');
  const tabLoginBtn = document.getElementById('tabLoginBtn');
  const tabRegisterBtn = document.getElementById('tabRegisterBtn');
  const tabForgotBtn = document.getElementById('tabForgotBtn');
  const panelLogin = document.getElementById('panelLogin');
  const panelRegister = document.getElementById('panelRegister');
  const panelForgot = document.getElementById('panelForgot');

  const loginForm = document.getElementById('loginForm');
  const loginUsername = document.getElementById('loginUsername');
  const loginPassword = document.getElementById('loginPassword');
  const loginError = document.getElementById('loginError');
  const loginSubmitBtn = document.getElementById('loginSubmitBtn');
  const switchToForgotBtn = document.getElementById('switchToForgotBtn');
  const switchToRegisterBtn = document.getElementById('switchToRegisterBtn');

  const registerForm = document.getElementById('registerForm');
  const registerUsername = document.getElementById('registerUsername');
  const registerEmail = document.getElementById('registerEmail');
  const registerPassword = document.getElementById('registerPassword');
  const registerError = document.getElementById('registerError');
  const registerSubmitBtn = document.getElementById('registerSubmitBtn');
  const switchToLoginBtn1 = document.getElementById('switchToLoginBtn1');

  const forgotStep1 = document.getElementById('forgotStep1');
  const forgotStep1Form = document.getElementById('forgotStep1Form');
  const forgotEmail = document.getElementById('forgotEmail');
  const forgotStep1Msg = document.getElementById('forgotStep1Msg');
  const forgotSendCodeBtn = document.getElementById('forgotSendCodeBtn');

  const forgotStep2 = document.getElementById('forgotStep2');
  const forgotStep2Form = document.getElementById('forgotStep2Form');
  const forgotDevBanner = document.getElementById('forgotDevBanner');
  const resetCodeInput = document.getElementById('resetCodeInput');
  const resetNewPassword = document.getElementById('resetNewPassword');
  const forgotStep2Msg = document.getElementById('forgotStep2Msg');
  const resetSubmitBtn = document.getElementById('resetSubmitBtn');
  const forgotBackToStep1Btn = document.getElementById('forgotBackToStep1Btn');
  const switchToLoginBtn2 = document.getElementById('switchToLoginBtn2');

  // Text, Checkbox & Code Helpers
  function escapeHtml(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Clean raw markdown symbols to clean plain text format (retaining code blocks & checkboxes)
  function cleanMarkdownToText(content) {
    if (!content) return '';
    let text = content;
    // Strip markdown headings (###, ##, #)
    text = text.replace(/^#{1,6}\s+(.*$)/gm, '$1');
    // Strip bold & italic markers
    text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
    text = text.replace(/\*([^*]+)\*/g, '$1');
    // Strip blockquotes
    text = text.replace(/^>\s+(.*$)/gm, '$1');
    // Standardize checkboxes: convert "- [ ] " or "- [x] " or "* [ ]" to "[ ] " or "[x] "
    text = text.replace(/^[-*+]\s*\[([ xX])\]\s*(.*$)/gm, '[$1] $2');
    // Convert bullet asterisks to clean bullet symbol
    text = text.replace(/^[\*]\s+(.*$)/gm, '• $1');
    return text;
  }

  // Calculate task checklist progress for notes
  function getCheckboxStats(content) {
    if (!content) return { total: 0, completed: 0, percent: 0 };
    const clean = cleanMarkdownToText(content);
    const lines = clean.split('\n');
    let total = 0;
    let completed = 0;
    lines.forEach((line) => {
      const match = line.match(/^\s*(?:[-*+•]\s*)?\[([ xX])\]/);
      if (match) {
        total++;
        if (match[1].toLowerCase() === 'x') {
          completed++;
        }
      }
    });
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
    return { total, completed, percent };
  }

  // Generate HTML for card progress bar
  function createCardProgressHtml(noteId, content) {
    const stats = getCheckboxStats(content);
    if (stats.total === 0) return '';
    const isComplete = stats.percent === 100;
    return `
      <div class="card-progress ${isComplete ? 'is-complete' : ''}" data-note-id="${noteId}">
        <div class="progress-bar-track">
          <div class="progress-bar-fill ${isComplete ? 'is-complete' : ''}" style="width: ${stats.percent}%;"></div>
        </div>
        <div class="progress-info">
          <span class="progress-count">${isComplete ? '✓ ' : ''}${stats.completed}/${stats.total} completed</span>
          <span class="progress-percent">${stats.percent}%</span>
        </div>
      </div>
    `;
  }

  // Render plain text, interactive checkboxes, and code blocks for note cards
  function renderCardContent(content, noteId) {
    if (!content || !content.trim()) {
      return '<span style="color: var(--text-muted); font-style: italic;">Empty note</span>';
    }
    const clean = cleanMarkdownToText(content);
    const lines = clean.split('\n');
    const htmlParts = [];
    let inCodeBlock = false;
    let codeLines = [];

    lines.forEach((line, idx) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          htmlParts.push(`<pre class="card-code-block"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
          codeLines = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
          codeLines = [];
        }
        return;
      }

      if (inCodeBlock) {
        codeLines.push(line);
        return;
      }

      const match = line.match(/^\s*(?:[-*+•]\s*)?\[([ xX])\]\s*(.*)$/);
      if (match) {
        const isChecked = match[1].toLowerCase() === 'x';
        const taskText = match[2];
        htmlParts.push(`<div class="card-todo-line ${isChecked ? 'completed' : ''}">
          <input type="checkbox" class="card-todo-check" data-note-id="${noteId}" data-line-idx="${idx}" ${isChecked ? 'checked' : ''}>
          <span>${escapeHtml(taskText)}</span>
        </div>`);
      } else {
        htmlParts.push(`<div>${escapeHtml(line) || '&nbsp;'}</div>`);
      }
    });

    if (inCodeBlock && codeLines.length > 0) {
      htmlParts.push(`<pre class="card-code-block"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
    }

    return htmlParts.join('');
  }

  // Toast Helper
  function showToast(message) {
    toastNotification.textContent = message;
    toastNotification.style.display = 'block';
    setTimeout(() => {
      toastNotification.style.display = 'none';
    }, 2500);
  }

  // Auth Helpers & Event Handlers
  function showError(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
  }

  function clearAuthErrors() {
    if (loginError) { loginError.textContent = ''; loginError.style.display = 'none'; }
    if (registerError) { registerError.textContent = ''; registerError.style.display = 'none'; }
    if (forgotStep1Msg) { forgotStep1Msg.textContent = ''; forgotStep1Msg.style.display = 'none'; }
    if (forgotStep2Msg) { forgotStep2Msg.textContent = ''; forgotStep2Msg.style.display = 'none'; }
    if (forgotDevBanner) { forgotDevBanner.textContent = ''; forgotDevBanner.style.display = 'none'; }
  }

  function updateUserUI() {
    if (!currentUser) {
      if (userProfileContainer) userProfileContainer.style.display = 'none';
      return;
    }
    if (userProfileContainer) userProfileContainer.style.display = 'inline-block';
    if (headerUsername) headerUsername.textContent = currentUser.username;
    if (dropdownUsername) dropdownUsername.textContent = currentUser.username;
    if (dropdownEmail) dropdownEmail.textContent = currentUser.email || '';
  }

  function handleUnauthorized() {
    currentUser = null;
    updateUserUI();
    notes = [];
    folders = [];
    renderNotes();
    if (foldersListEl) foldersListEl.innerHTML = '<span class="sidebar-empty">Please log in</span>';
    showAuthModal('login');
  }

  function showAuthModal(tab = 'login') {
    if (noteModal) noteModal.style.display = 'none';
    if (folderModal) folderModal.style.display = 'none';
    if (authModal) authModal.style.display = 'flex';
    switchAuthTab(tab);
  }

  function hideAuthModal() {
    if (authModal) authModal.style.display = 'none';
    clearAuthErrors();
  }

  function switchAuthTab(tab) {
    clearAuthErrors();
    [tabLoginBtn, tabRegisterBtn, tabForgotBtn].forEach((b) => b && b.classList.remove('active'));
    [panelLogin, panelRegister, panelForgot].forEach((p) => p && (p.style.display = 'none'));

    if (tab === 'login') {
      if (tabLoginBtn) tabLoginBtn.classList.add('active');
      if (panelLogin) panelLogin.style.display = 'block';
      setTimeout(() => loginUsername && loginUsername.focus(), 50);
    } else if (tab === 'register') {
      if (tabRegisterBtn) tabRegisterBtn.classList.add('active');
      if (panelRegister) panelRegister.style.display = 'block';
      setTimeout(() => registerUsername && registerUsername.focus(), 50);
    } else if (tab === 'forgot') {
      if (tabForgotBtn) tabForgotBtn.classList.add('active');
      if (panelForgot) panelForgot.style.display = 'block';
      if (forgotStep1) forgotStep1.style.display = 'block';
      if (forgotStep2) forgotStep2.style.display = 'none';
      setTimeout(() => forgotEmail && forgotEmail.focus(), 50);
    }
  }

  async function checkAuth() {
    try {
      const res = await fetch('/api/auth/me');
      if (!res.ok) {
        handleUnauthorized();
        return;
      }
      const data = await res.json();
      if (data.logged_in && data.user) {
        currentUser = data.user;
        updateUserUI();
        hideAuthModal();
        await fetchFolders();
        await fetchNotes();
      } else {
        handleUnauthorized();
      }
    } catch (err) {
      console.error('Auth verification error:', err);
      handleUnauthorized();
    }
  }

  async function handleLogin(e) {
    if (e) e.preventDefault();
    clearAuthErrors();
    const username = loginUsername ? loginUsername.value.trim() : '';
    const password = loginPassword ? loginPassword.value : '';

    if (!username || !password) {
      showError(loginError, 'Username and password are required');
      return;
    }

    try {
      if (loginSubmitBtn) {
        loginSubmitBtn.disabled = true;
        loginSubmitBtn.innerHTML = '<span>Logging in...</span>';
      }
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showError(loginError, data.error || 'Invalid credentials');
        return;
      }
      currentUser = data.user;
      updateUserUI();
      hideAuthModal();
      if (loginPassword) loginPassword.value = '';
      showToast(`Welcome back, ${currentUser.username}!`);
      await fetchFolders();
      await fetchNotes();
    } catch (err) {
      showError(loginError, 'Network error. Please try again.');
    } finally {
      if (loginSubmitBtn) {
        loginSubmitBtn.disabled = false;
        loginSubmitBtn.innerHTML = '<span>Log In</span>';
      }
    }
  }

  async function handleRegister(e) {
    if (e) e.preventDefault();
    clearAuthErrors();
    const username = registerUsername ? registerUsername.value.trim() : '';
    const email = registerEmail ? registerEmail.value.trim() : '';
    const password = registerPassword ? registerPassword.value : '';

    if (!username || !email || !password) {
      showError(registerError, 'All fields are required');
      return;
    }
    if (password.length < 6) {
      showError(registerError, 'Password must be at least 6 characters');
      return;
    }

    try {
      if (registerSubmitBtn) {
        registerSubmitBtn.disabled = true;
        registerSubmitBtn.innerHTML = '<span>Creating account...</span>';
      }
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showError(registerError, data.error || 'Failed to create account');
        return;
      }
      currentUser = data.user;
      updateUserUI();
      hideAuthModal();
      if (registerPassword) registerPassword.value = '';
      showToast(`Welcome to SimpleNotes, ${currentUser.username}!`);
      await fetchFolders();
      await fetchNotes();
    } catch (err) {
      showError(registerError, 'Network error. Please try again.');
    } finally {
      if (registerSubmitBtn) {
        registerSubmitBtn.disabled = false;
        registerSubmitBtn.innerHTML = '<span>Create Account</span>';
      }
    }
  }

  async function handleForgotStep1(e) {
    if (e) e.preventDefault();
    clearAuthErrors();
    const email = forgotEmail ? forgotEmail.value.trim() : '';
    if (!email || !email.includes('@')) {
      showError(forgotStep1Msg, 'Please enter a valid email address');
      return;
    }

    try {
      if (forgotSendCodeBtn) {
        forgotSendCodeBtn.disabled = true;
        forgotSendCodeBtn.innerHTML = '<span>Sending code...</span>';
      }
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showError(forgotStep1Msg, data.error || 'Unable to send reset code');
        return;
      }
      pendingResetEmail = email;
      if (forgotStep1) forgotStep1.style.display = 'none';
      if (forgotStep2) forgotStep2.style.display = 'block';

      if (data.dev_code && forgotDevBanner) {
        forgotDevBanner.innerHTML = `<strong>Local Dev Notice:</strong> Your 6-digit code is <code>${escapeHtml(data.dev_code)}</code>`;
        forgotDevBanner.style.display = 'block';
      } else if (forgotDevBanner) {
        forgotDevBanner.style.display = 'none';
      }

      if (resetCodeInput) {
        resetCodeInput.value = '';
        setTimeout(() => resetCodeInput.focus(), 50);
      }
      if (resetNewPassword) resetNewPassword.value = '';
      showToast(`Reset code sent to ${email}`);
    } catch (err) {
      showError(forgotStep1Msg, 'Network error. Please try again.');
    } finally {
      if (forgotSendCodeBtn) {
        forgotSendCodeBtn.disabled = false;
        forgotSendCodeBtn.innerHTML = '<span>Send Verification Code</span>';
      }
    }
  }

  async function handleResetPassword(e) {
    if (e) e.preventDefault();
    clearAuthErrors();
    const code = resetCodeInput ? resetCodeInput.value.trim() : '';
    const newPassword = resetNewPassword ? resetNewPassword.value : '';

    if (!code || code.length !== 6) {
      showError(forgotStep2Msg, 'Please enter the 6-digit verification code');
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      showError(forgotStep2Msg, 'New password must be at least 6 characters');
      return;
    }

    try {
      if (resetSubmitBtn) {
        resetSubmitBtn.disabled = true;
        resetSubmitBtn.innerHTML = '<span>Resetting password...</span>';
      }
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: pendingResetEmail,
          code,
          new_password: newPassword
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showError(forgotStep2Msg, data.error || 'Invalid or expired code');
        return;
      }
      showToast('Password reset! Please log in with your new password.');
      switchAuthTab('login');
      if (loginUsername) loginUsername.value = pendingResetEmail;
      if (loginPassword) {
        loginPassword.value = '';
        setTimeout(() => loginPassword.focus(), 50);
      }
    } catch (err) {
      showError(forgotStep2Msg, 'Network error. Please try again.');
    } finally {
      if (resetSubmitBtn) {
        resetSubmitBtn.disabled = false;
        resetSubmitBtn.innerHTML = '<span>Reset Password</span>';
      }
    }
  }

  async function handleLogout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.error('Logout error:', err);
    }
    currentUser = null;
    updateUserUI();
    notes = [];
    folders = [];
    renderNotes();
    if (foldersListEl) foldersListEl.innerHTML = '';
    showToast('Logged out successfully');
    showAuthModal('login');
  }

  // Theme Management
  function initTheme() {
    const saved = localStorage.getItem('notes_theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    setTheme(theme);
  }

  function setTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('notes_theme', theme);
    const icon = themeToggleBtn.querySelector('.theme-icon');
    if (icon) {
      icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
  }

  themeToggleBtn.addEventListener('click', () => {
    const current = document.body.getAttribute('data-theme') || 'light';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });

  // Fetch Notes from API
  async function fetchNotes() {
    try {
      const params = new URLSearchParams();
      const hasQuery = Boolean(searchQuery && searchQuery.trim());
      if (hasQuery) {
        params.set('q', searchQuery.trim());
        if (isUniversalSearch) {
          params.set('universal', 'true');
          params.set('subfolders', 'true');
        } else if (activeFolderId !== null) {
          params.set('folder_id', activeFolderId);
          params.set('subfolders', 'true');
        } else if (activeFilter.startsWith('tag:')) {
          params.set('tag', activeFilter.replace('tag:', ''));
        }
      } else {
        if (activeFilter.startsWith('tag:')) params.set('tag', activeFilter.replace('tag:', ''));
        if (activeFolderId !== null) params.set('folder_id', activeFolderId);
      }
      params.set('sort', sortBy);

      const res = await fetch(`/api/notes?${params.toString()}`);
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error('Failed to fetch notes');
      notes = await res.json();
      renderNotes();
      updateFilterLabel();
      fetchFolders();
      fetchTags();
    } catch (err) {
      console.error(err);
      showToast('Error loading notes');
    }
  }

  async function fetchFolders() {
    try {
      const res = await fetch('/api/folders');
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) return;
      folders = await res.json();
      renderFolders();
      updateModalFolderSelect();
      updateFolderParentSelect();
      updateAllNotesCountBadge();
    } catch (err) {
      console.error('Error fetching folders:', err);
    }
  }

  function updateAllNotesCountBadge() {
    if (!folders || folders.length === 0) return;
    const total = folders.reduce((sum, f) => sum + (f.note_count || 0), 0);
    allCountEl.textContent = total;
  }

  function renderFolders() {
    if (!foldersListEl) return;
    if (!folders || folders.length === 0) {
      foldersListEl.innerHTML = '<span class="sidebar-empty">No folders yet</span>';
      return;
    }

    // Group folders by parent_id
    const childrenByParent = {};
    folders.forEach((f) => {
      const pid = f.parent_id !== null && f.parent_id !== undefined ? String(f.parent_id) : 'root';
      if (!childrenByParent[pid]) childrenByParent[pid] = [];
      childrenByParent[pid].push(f);
    });

    function renderNode(folder) {
      const isHome = Boolean(folder.is_default) || folder.name.toLowerCase() === 'home';
      const isActive = activeFilter === 'folder:' + folder.id;
      const icon = isHome ? '🏠' : '📁';
      const children = childrenByParent[String(folder.id)] || [];

      const actionsHtml = isHome
        ? `
          <div class="folder-item-actions">
            <button class="folder-action-icon-btn add-btn add-subfolder-btn" data-parent-id="${folder.id}" data-folder-name="${escapeHtml(folder.name)}" title="Add subfolder inside ${escapeHtml(folder.name)}">+</button>
          </div>
        `
        : `
          <div class="folder-item-actions">
            <button class="folder-action-icon-btn add-btn add-subfolder-btn" data-parent-id="${folder.id}" data-folder-name="${escapeHtml(folder.name)}" title="Add subfolder inside ${escapeHtml(folder.name)}">+</button>
            <button class="folder-action-icon-btn edit-folder-btn" data-folder-id="${folder.id}" data-folder-name="${escapeHtml(folder.name)}" data-parent-id="${folder.parent_id || ''}" title="Edit folder">✏️</button>
            <button class="folder-action-icon-btn delete-btn delete-folder-btn" data-folder-id="${folder.id}" data-folder-name="${escapeHtml(folder.name)}" title="Delete folder">🗑️</button>
          </div>
        `;

      const childrenHtml = children.length > 0
        ? `<div class="folder-tree-children">${children.map(renderNode).join('')}</div>`
        : '';

      return `
        <div class="folder-tree-node depth-${folder.depth || 0}" data-folder-id="${folder.id}">
          <div class="folder-nav-item ${isActive ? 'active' : ''}" data-folder-id="${folder.id}" data-folder-name="${escapeHtml(folder.name)}" data-folder-path="${escapeHtml(folder.path || folder.name)}">
            <div class="folder-nav-left">
              <span class="folder-nav-icon">${icon}</span>
              <span class="folder-nav-name" title="${escapeHtml(folder.path || folder.name)}">${escapeHtml(folder.name)}</span>
            </div>
            <div class="folder-nav-right">
              ${actionsHtml}
              <span class="folder-count" title="${folder.note_count || 0} direct notes">${folder.note_count || 0}</span>
            </div>
          </div>
          ${childrenHtml}
        </div>
      `;
    }

    const rootFolders = childrenByParent['root'] || [];
    foldersListEl.innerHTML = rootFolders.map(renderNode).join('');

    // Attach listeners
    foldersListEl.querySelectorAll('.folder-nav-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.folder-action-icon-btn')) return;
        const fId = parseInt(item.getAttribute('data-folder-id'), 10);
        const fName = item.getAttribute('data-folder-name');
        const fPath = item.getAttribute('data-folder-path');
        selectFolderFilter(fId, fPath || fName);
      });
    });

    foldersListEl.querySelectorAll('.add-subfolder-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pId = parseInt(btn.getAttribute('data-parent-id'), 10);
        openCreateFolderModal(pId);
      });
    });

    foldersListEl.querySelectorAll('.edit-folder-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const fId = parseInt(btn.getAttribute('data-folder-id'), 10);
        const fName = btn.getAttribute('data-folder-name');
        const pId = btn.getAttribute('data-parent-id');
        openRenameFolderModal(fId, fName, pId ? parseInt(pId, 10) : null);
      });
    });

    foldersListEl.querySelectorAll('.delete-folder-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const fId = parseInt(btn.getAttribute('data-folder-id'), 10);
        const fName = btn.getAttribute('data-folder-name');
        deleteFolder(fId, fName);
      });
    });
  }

  function updateFolderParentSelect(selectedParentId = null) {
    if (!folderParentSelect) return;
    let html = '<option value="">(None - Root Level)</option>';
    const editingFolder = currentEditingFolderId ? folders.find((f) => f.id === currentEditingFolderId) : null;
    const editingPath = editingFolder ? (editingFolder.path || editingFolder.name) : null;

    folders.forEach((f) => {
      if (currentEditingFolderId) {
        if (f.id === currentEditingFolderId) return;
        if (editingPath && (f.path === editingPath || f.path.startsWith(editingPath + ' / '))) return;
      }
      const isHome = Boolean(f.is_default) || f.name.toLowerCase() === 'home';
      const indent = '&nbsp;&nbsp;'.repeat((f.depth || 0) * 2);
      const branchPrefix = (f.depth || 0) > 0 ? '└── ' : '';
      const icon = isHome ? '🏠 ' : '📁 ';
      html += `<option value="${f.id}">${indent}${branchPrefix}${icon}${escapeHtml(f.name)}</option>`;
    });
    folderParentSelect.innerHTML = html;
    folderParentSelect.value = selectedParentId !== null && selectedParentId !== undefined && selectedParentId !== ''
      ? String(selectedParentId)
      : '';
  }

  function updateModalFolderSelect() {
    if (!modalFolder) return;
    const currentVal = modalFolder.value;
    modalFolder.innerHTML = folders.map((f) => {
      const isHome = Boolean(f.is_default) || f.name.toLowerCase() === 'home';
      const indent = '\u00A0\u00A0'.repeat((f.depth || 0) * 2);
      const branchPrefix = (f.depth || 0) > 0 ? '└── ' : '';
      const icon = isHome ? '🏠 ' : '📁 ';
      const label = `${indent}${branchPrefix}${icon}${escapeHtml(f.name)}`;
      return `<option value="${f.id}">${label}</option>`;
    }).join('');

    if (currentVal && folders.some(f => String(f.id) === String(currentVal))) {
      modalFolder.value = currentVal;
    } else if (activeFolderId && folders.some(f => String(f.id) === String(activeFolderId))) {
      modalFolder.value = String(activeFolderId);
    } else {
      const defaultFolder = folders.find(f => f.is_default) || folders[0];
      modalFolder.value = defaultFolder ? String(defaultFolder.id) : '';
    }
  }

  function selectFolderFilter(folderId, folderDisplayName) {
    activeFilter = 'folder:' + folderId;
    activeFolderId = folderId;

    document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.tag-nav-item').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.folder-nav-item').forEach((item) => {
      item.classList.toggle('active', parseInt(item.getAttribute('data-folder-id'), 10) === folderId);
    });

    updateFilterLabel();
    fetchNotes();
  }

  function updateFilterLabel() {
    if (!activeFilterLabel) return;

    if (searchQuery && searchQuery.trim()) {
      const q = escapeHtml(searchQuery.trim());
      const count = notes.length;
      const countText = count === 1 ? '1 note found' : `${count} notes found`;

      if (isUniversalSearch) {
        if (activeFolderId !== null) {
          const folderObj = folders.find((f) => f.id === activeFolderId);
          const fName = folderObj ? (folderObj.name || 'Folder') : 'Folder';
          activeFilterLabel.innerHTML = `
            <span>🔍 Universal Search: <strong>"${q}"</strong> (${countText} across all folders & subfolders)</span>
            <button type="button" class="search-scope-toggle-btn" id="searchScopeToggleBtn" title="Restrict search to ${escapeHtml(fName)} and its subfolders">Scope to ${escapeHtml(fName)}</button>
          `;
        } else {
          activeFilterLabel.innerHTML = `<span>🔍 Universal Search: <strong>"${q}"</strong> (${countText} across all folders & subfolders)</span>`;
        }
      } else {
        const folderObj = folders.find((f) => f.id === activeFolderId);
        const fName = folderObj ? (folderObj.path || folderObj.name || 'Folder') : 'Folder';
        activeFilterLabel.innerHTML = `
          <span>📁 Searching in: <strong>${escapeHtml(fName)} & Subfolders</strong> (<strong>"${q}"</strong>, ${countText})</span>
          <button type="button" class="search-scope-toggle-btn" id="searchScopeToggleBtn" title="Search universally across all folders and subfolders">Make Universal</button>
        `;
      }

      const toggleBtn = document.getElementById('searchScopeToggleBtn');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          isUniversalSearch = !isUniversalSearch;
          fetchNotes();
        });
      }
      return;
    }

    if (activeFilter === 'all') {
      activeFilterLabel.textContent = 'Showing All Notes';
    } else if (activeFilter === 'pinned') {
      activeFilterLabel.textContent = 'Showing Pinned Notes';
    } else if (activeFilter.startsWith('tag:')) {
      activeFilterLabel.textContent = `Tagged: #${activeFilter.replace('tag:', '')}`;
    } else if (activeFilter.startsWith('folder:')) {
      const fId = parseInt(activeFilter.replace('folder:', ''), 10);
      const folderObj = folders.find((f) => f.id === fId);
      const fDisplay = folderObj ? (folderObj.path || folderObj.name) : 'Folder';
      const isHome = Boolean(folderObj && folderObj.is_default) || fDisplay.toLowerCase() === 'home';
      activeFilterLabel.textContent = isHome ? '🏠 Folder: Home' : `📁 Folder: ${fDisplay}`;
    }
  }

  async function fetchTags() {
    try {
      const res = await fetch('/api/tags');
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) return;
      const tags = await res.json();
      renderTags(tags);
    } catch (err) {
      console.error(err);
    }
  }

  // Render Note Cards
  function renderNotes() {
    let displayNotes = notes;
    if (activeFilter === 'pinned') {
      displayNotes = notes.filter((n) => n.is_pinned);
    }

    const pinnedTotal = notes.filter((n) => n.is_pinned).length;
    if (activeFilter === 'all') {
      allCountEl.textContent = notes.length;
    }
    pinnedCountEl.textContent = pinnedTotal;

    pinnedGrid.className = `notes-grid ${isGridView ? '' : 'list-view'}`;
    notesGrid.className = `notes-grid ${isGridView ? '' : 'list-view'}`;

    if (displayNotes.length === 0) {
      pinnedSection.style.display = 'none';
      othersSection.style.display = 'none';
      emptyState.style.display = 'block';

      const titleEl = emptyState.querySelector('.empty-title');
      const descEl = emptyState.querySelector('.empty-desc');
      if (searchQuery && searchQuery.trim()) {
        if (titleEl) titleEl.textContent = 'No matching notes found';
        if (descEl) descEl.textContent = `No notes found matching "${searchQuery.trim()}" across any folders or subfolders.`;
      } else {
        if (titleEl) titleEl.textContent = 'No notes found';
        if (descEl) descEl.textContent = 'Create your first note or select a different folder.';
      }
      return;
    }

    emptyState.style.display = 'none';

    const isSeparated = activeFilter === 'all' && !searchQuery.trim();
    const pinnedNotes = displayNotes.filter((n) => n.is_pinned);
    const otherNotes = displayNotes.filter((n) => !n.is_pinned);

    if (isSeparated && pinnedNotes.length > 0) {
      pinnedSection.style.display = 'block';
      pinnedGrid.innerHTML = pinnedNotes.map(createNoteCardHtml).join('');
      
      othersSection.style.display = 'block';
      othersSectionTitle.style.display = 'block';
      notesGrid.innerHTML = otherNotes.map(createNoteCardHtml).join('');
    } else {
      pinnedSection.style.display = 'none';
      othersSection.style.display = 'block';
      othersSectionTitle.style.display = 'none';
      notesGrid.innerHTML = displayNotes.map(createNoteCardHtml).join('');
    }

    attachCardListeners();
  }

  function createNoteCardHtml(note) {
    const colorAttr = note.color && note.color !== 'default' ? `data-color="${note.color}"` : '';
    const pinnedClass = note.is_pinned ? 'is-pinned' : '';
    const progressHtml = createCardProgressHtml(note.id, note.content);
    const contentHtml = renderCardContent(note.content, note.id);
    
    const tagsHtml = (note.tags_list || []).map(tag => 
      `<span class="card-tag-pill" data-tag="${escapeHtml(tag)}">#${escapeHtml(tag)}</span>`
    ).join('');

    const formattedDate = formatDate(note.updated_at);
    const isHome = note.folder_id === 1 || (note.folder_name && note.folder_name.toLowerCase() === 'home');
    const folderIcon = isHome ? '🏠' : '📁';
    const folderDisplayName = escapeHtml(note.folder_path || note.folder_name || 'Home');
    const folderName = escapeHtml(note.folder_name || 'Home');

    return `
      <div class="note-card ${pinnedClass}" data-id="${note.id}" ${colorAttr}>
        <div class="card-header">
          <h3 class="card-title">${escapeHtml(note.title)}</h3>
          <button class="card-pin-btn" data-id="${note.id}" title="${note.is_pinned ? 'Unpin' : 'Pin'}">
            📌
          </button>
        </div>
        ${progressHtml}
        <div class="card-content">
          ${contentHtml}
        </div>
        ${tagsHtml ? `<div class="card-tags">${tagsHtml}</div>` : ''}
        <div class="card-footer">
          <span class="card-folder-pill" data-folder-id="${note.folder_id || 1}" data-folder-name="${folderName}" data-folder-display="${folderDisplayName}" title="Folder: ${folderDisplayName}">
            ${folderIcon} ${folderDisplayName}
          </span>
          <span>${formattedDate}</span>
        </div>
      </div>
    `;
  }

  function attachCardListeners() {
    document.querySelectorAll('.note-card').forEach((card) => {
      card.addEventListener('click', (e) => {
        // Ignore clicks on pin button, tag pills, folder pills, or checkboxes
        if (
          e.target.closest('.card-pin-btn') ||
          e.target.closest('.card-tag-pill') ||
          e.target.closest('.card-folder-pill') ||
          e.target.closest('.card-todo-check')
        ) return;
        const noteId = parseInt(card.getAttribute('data-id'), 10);
        openEditModal(noteId, card);
      });
    });

    document.querySelectorAll('.card-folder-pill').forEach((pill) => {
      pill.addEventListener('click', (e) => {
        e.stopPropagation();
        const fId = parseInt(pill.getAttribute('data-folder-id'), 10);
        const fDisplay = pill.getAttribute('data-folder-display') || 'Home';
        selectFolderFilter(fId, fDisplay);
      });
    });

    document.querySelectorAll('.card-pin-btn').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const noteId = parseInt(btn.getAttribute('data-id'), 10);
        try {
          const res = await fetch(`/api/notes/${noteId}/pin`, { method: 'POST' });
          if (!res.ok) throw new Error('Pin failed');
          fetchNotes();
        } catch (err) {
          console.error(err);
          showToast('Failed to toggle pin');
        }
      });
    });

    document.querySelectorAll('.card-tag-pill').forEach((pill) => {
      pill.addEventListener('click', (e) => {
        e.stopPropagation();
        const tag = pill.getAttribute('data-tag');
        if (tag) selectTagFilter(tag);
      });
    });

    // Checkbox toggling directly from card
    document.querySelectorAll('.card-todo-check').forEach((cb) => {
      cb.addEventListener('click', async (e) => {
        e.stopPropagation();
        const noteId = parseInt(cb.getAttribute('data-note-id'), 10);
        const lineIdx = parseInt(cb.getAttribute('data-line-idx'), 10);
        const note = notes.find((n) => n.id === noteId);
        if (!note) return;

        const clean = cleanMarkdownToText(note.content);
        const lines = clean.split('\n');
        if (lineIdx < lines.length) {
          const isChecked = cb.checked;
          lines[lineIdx] = lines[lineIdx].replace(/^\s*(?:[-*+•]\s*)?\[([ xX])\]/, isChecked ? '[x]' : '[ ]');
          note.content = lines.join('\n');

          const cardLine = cb.closest('.card-todo-line');
          if (cardLine) cardLine.classList.toggle('completed', isChecked);

          updateCardProgressBar(noteId, note.content);

          try {
            await fetch(`/api/notes/${noteId}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: note.content })
            });
          } catch (err) {
            console.error(err);
          }
        }
      });
    });
  }

  // Update or inject card progress bar when checkboxes are toggled
  function updateCardProgressBar(noteId, content) {
    const card = document.querySelector(`.note-card[data-id="${noteId}"]`);
    if (!card) return;
    const stats = getCheckboxStats(content);
    let progressEl = card.querySelector('.card-progress');
    if (stats.total === 0) {
      if (progressEl) progressEl.remove();
      return;
    }
    if (!progressEl) {
      const headerEl = card.querySelector('.card-header');
      if (headerEl) {
        headerEl.insertAdjacentHTML('afterend', createCardProgressHtml(noteId, content));
      }
      return;
    }
    const fillEl = progressEl.querySelector('.progress-bar-fill');
    const countEl = progressEl.querySelector('.progress-count');
    const percentEl = progressEl.querySelector('.progress-percent');
    const isComplete = stats.percent === 100;

    progressEl.classList.toggle('is-complete', isComplete);
    if (fillEl) {
      fillEl.style.width = `${stats.percent}%`;
      fillEl.classList.toggle('is-complete', isComplete);
    }
    if (countEl) {
      countEl.textContent = `${isComplete ? '✓ ' : ''}${stats.completed}/${stats.total} completed`;
    }
    if (percentEl) {
      percentEl.textContent = `${stats.percent}%`;
    }
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays}d ago`;

      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  }

  // Render Tags in Sidebar
  function renderTags(tags) {
    if (!tags || tags.length === 0) {
      tagsListEl.innerHTML = '<span class="sidebar-empty">No tags yet</span>';
      return;
    }

    tagsListEl.innerHTML = tags.map((t) => {
      const isActive = activeFilter === 'tag:' + t.name ? 'active' : '';
      return `
        <button class="tag-nav-item ${isActive}" data-tag="${escapeHtml(t.name)}">
          <span class="tag-name">#${escapeHtml(t.name)}</span>
          <span class="tag-count">${t.count}</span>
        </button>
      `;
    }).join('');

    tagsListEl.querySelectorAll('.tag-nav-item').forEach((item) => {
      item.addEventListener('click', () => {
        const tag = item.getAttribute('data-tag');
        selectTagFilter(tag);
      });
    });
  }

  // Filter & Search Handling
  function selectFilter(filterName) {
    activeFilter = filterName;
    activeFolderId = null;
    document.querySelectorAll('.nav-item').forEach((item) => {
      item.classList.toggle('active', item.getAttribute('data-filter') === filterName);
    });
    document.querySelectorAll('.tag-nav-item').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.folder-nav-item').forEach((item) => item.classList.remove('active'));

    updateFilterLabel();
    fetchNotes();
  }

  function selectTagFilter(tagName) {
    activeFilter = 'tag:' + tagName;
    activeFolderId = null;
    document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.folder-nav-item').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.tag-nav-item').forEach((item) => {
      const isMatch = item.querySelector('.tag-name')?.textContent === '#' + tagName;
      item.classList.toggle('active', isMatch);
    });

    updateFilterLabel();
    fetchNotes();
  }

  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', () => selectFilter(item.getAttribute('data-filter')));
  });

  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    clearSearchBtn.style.display = searchQuery ? 'block' : 'none';
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      fetchNotes();
    }, 200);
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    searchQuery = '';
    clearSearchBtn.style.display = 'none';
    isUniversalSearch = true;
    fetchNotes();
    searchInput.focus();
  });

  sortSelect.addEventListener('change', (e) => {
    sortBy = e.target.value;
    fetchNotes();
  });

  // View Mode
  viewGridBtn.addEventListener('click', () => {
    isGridView = true;
    localStorage.setItem('notes_view', 'grid');
    viewGridBtn.classList.add('active');
    viewListBtn.classList.remove('active');
    renderNotes();
  });

  viewListBtn.addEventListener('click', () => {
    isGridView = false;
    localStorage.setItem('notes_view', 'list');
    viewListBtn.classList.add('active');
    viewGridBtn.classList.remove('active');
    renderNotes();
  });

  // Editor Modal: Text, Checkbox & Code Block Manipulation
  function createTodoLineHtml(isChecked, taskText) {
    return `<div class="todo-line ${isChecked ? 'completed' : ''}"><input type="checkbox" class="todo-check" contenteditable="false" ${isChecked ? 'checked' : ''}><span class="todo-text">${escapeHtml(taskText)}</span></div>`;
  }

  function setEditorContent(content) {
    const clean = cleanMarkdownToText(content || '');
    if (!clean.trim()) {
      modalEditor.innerHTML = '';
      return;
    }
    const lines = clean.split('\n');
    const htmlParts = [];
    let inCodeBlock = false;
    let codeLines = [];

    lines.forEach((line) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          htmlParts.push(`<pre class="code-block" spellcheck="false"><code class="code-content" contenteditable="true">${escapeHtml(codeLines.join('\n'))}</code></pre>`);
          codeLines = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
          codeLines = [];
        }
        return;
      }

      if (inCodeBlock) {
        codeLines.push(line);
        return;
      }

      const match = line.match(/^\s*(?:-\s*)?\[([ xX])\]\s*(.*)$/);
      if (match) {
        const isChecked = match[1].toLowerCase() === 'x';
        htmlParts.push(createTodoLineHtml(isChecked, match[2]));
      } else {
        htmlParts.push(`<div>${escapeHtml(line) || '<br>'}</div>`);
      }
    });

    if (inCodeBlock && codeLines.length > 0) {
      htmlParts.push(`<pre class="code-block" spellcheck="false"><code class="code-content" contenteditable="true">${escapeHtml(codeLines.join('\n'))}</code></pre>`);
    }

    modalEditor.innerHTML = htmlParts.join('');
  }

  function getEditorContent() {
    const lines = [];
    const children = Array.from(modalEditor.childNodes);
    if (children.length === 0) {
      return modalEditor.innerText ? modalEditor.innerText.trim() : '';
    }
    for (const child of children) {
      if (child.nodeType === Node.TEXT_NODE) {
        const txt = child.textContent;
        if (txt) lines.push(txt);
      } else if (child.classList && child.classList.contains('code-block')) {
        const codeEl = child.querySelector('code') || child;
        const codeText = codeEl.innerText.replace(/\r?\n$/, '');
        lines.push('```');
        lines.push(codeText);
        lines.push('```');
      } else if (child.classList && child.classList.contains('todo-line')) {
        const cb = child.querySelector('.todo-check');
        const isChecked = cb && cb.checked;
        const textSpan = child.querySelector('.todo-text');
        const text = textSpan ? textSpan.innerText.trim() : '';
        lines.push(`${isChecked ? '[x]' : '[ ]'} ${text}`);
      } else if (child.nodeName === 'DIV' || child.nodeName === 'P') {
        const childCode = child.querySelector('.code-block');
        const childTodo = child.querySelector('.todo-line');
        if (childCode) {
          const codeEl = childCode.querySelector('code') || childCode;
          const codeText = codeEl.innerText.replace(/\r?\n$/, '');
          lines.push('```');
          lines.push(codeText);
          lines.push('```');
        } else if (childTodo) {
          const cb = childTodo.querySelector('.todo-check');
          const isChecked = cb && cb.checked;
          const textSpan = childTodo.querySelector('.todo-text');
          const text = textSpan ? textSpan.innerText.trim() : '';
          lines.push(`${isChecked ? '[x]' : '[ ]'} ${text}`);
        } else {
          if (child.innerHTML === '<br>' || child.innerText === '') {
            lines.push('');
          } else {
            lines.push(child.innerText.replace(/\r?\n$/, ''));
          }
        }
      } else if (child.nodeName === 'BR') {
        lines.push('');
      } else {
        lines.push(child.innerText ? child.innerText.replace(/\r?\n$/, '') : '');
      }
    }
    return lines.join('\n');
  }

  // Insert an actual checkbox into the editor
  function insertCheckboxLine(initialText = '') {
    modalEditor.focus();
    const todoLine = document.createElement('div');
    todoLine.className = 'todo-line';
    todoLine.innerHTML = `<input type="checkbox" class="todo-check" contenteditable="false"><span class="todo-text">${escapeHtml(initialText)}</span>`;

    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0 && modalEditor.contains(sel.anchorNode)) {
      let container = sel.anchorNode;
      while (container && container.parentNode !== modalEditor && container !== modalEditor) {
        container = container.parentNode;
      }
      if (container && container !== modalEditor) {
        if (!container.innerText.trim()) {
          modalEditor.replaceChild(todoLine, container);
        } else {
          container.insertAdjacentElement('afterend', todoLine);
        }
      } else {
        modalEditor.appendChild(todoLine);
      }
    } else {
      modalEditor.appendChild(todoLine);
    }

    const textSpan = todoLine.querySelector('.todo-text');
    textSpan.focus();
    const newRange = document.createRange();
    newRange.selectNodeContents(textSpan);
    newRange.collapse(false);
    const newSel = window.getSelection();
    newSel.removeAllRanges();
    newSel.addRange(newRange);

    updateWordCount();
    updateModalProgressBar();
  }

  // Update modal progress bar when checkboxes are in the editor
  function updateModalProgressBar() {
    if (!modalProgressBar) return;
    const checkboxes = modalEditor.querySelectorAll('.todo-check');
    const total = checkboxes.length;
    if (total === 0) {
      modalProgressBar.style.display = 'none';
      if (modalProgressFooter) modalProgressFooter.style.display = 'none';
      return;
    }

    let completed = 0;
    checkboxes.forEach((cb) => {
      if (cb.checked) completed++;
    });

    const percent = Math.round((completed / total) * 100);
    const isComplete = percent === 100;

    modalProgressBar.style.display = 'flex';
    modalProgressBar.classList.toggle('is-complete', isComplete);

    if (modalProgressFill) {
      modalProgressFill.style.width = `${percent}%`;
      modalProgressFill.classList.toggle('is-complete', isComplete);
    }
    if (modalProgressCount) {
      modalProgressCount.textContent = `${isComplete ? '✓ ' : ''}${completed}/${total} completed`;
    }
    if (modalProgressPercent) {
      modalProgressPercent.textContent = `${percent}%`;
    }
    if (modalProgressFooter) {
      modalProgressFooter.style.display = 'inline';
      modalProgressFooter.textContent = `• ${completed}/${total} tasks (${percent}%)`;
    }
  }

  // Insert a Code Block into the editor
  function insertCodeBlock(initialCode = '') {
    modalEditor.focus();
    const pre = document.createElement('pre');
    pre.className = 'code-block';
    pre.setAttribute('spellcheck', 'false');

    const code = document.createElement('code');
    code.className = 'code-content';
    code.setAttribute('contenteditable', 'true');
    code.textContent = initialCode || '// Enter code here';
    pre.appendChild(code);

    const followLine = document.createElement('div');
    followLine.innerHTML = '<br>';

    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0 && modalEditor.contains(sel.anchorNode)) {
      let container = sel.anchorNode;
      while (container && container.parentNode !== modalEditor && container !== modalEditor) {
        container = container.parentNode;
      }
      if (container && container !== modalEditor) {
        if (!container.innerText.trim()) {
          modalEditor.replaceChild(pre, container);
        } else {
          container.insertAdjacentElement('afterend', pre);
        }
      } else {
        modalEditor.appendChild(pre);
      }
    } else {
      modalEditor.appendChild(pre);
    }

    pre.insertAdjacentElement('afterend', followLine);

    code.focus();
    const range = document.createRange();
    range.selectNodeContents(code);
    const newSel = window.getSelection();
    newSel.removeAllRanges();
    newSel.addRange(range);

    updateWordCount();
  }

  insertTodoBtn.addEventListener('click', () => {
    insertCheckboxLine();
  });

  insertCodeBtn.addEventListener('click', () => {
    insertCodeBlock();
  });

  // Toggle checkbox state inside editor
  modalEditor.addEventListener('click', (e) => {
    if (e.target.classList.contains('todo-check')) {
      const line = e.target.closest('.todo-line');
      if (line) {
        line.classList.toggle('completed', e.target.checked);
      }
      updateWordCount();
      updateModalProgressBar();
    }
  });

  // Handle Enter & Tab keys inside editor
  modalEditor.addEventListener('keydown', (e) => {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;

    // Code block indentation with Tab
    if (e.key === 'Tab') {
      const codeBlock = sel.anchorNode?.closest?.('.code-block') || sel.anchorNode?.parentElement?.closest?.('.code-block');
      if (codeBlock) {
        e.preventDefault();
        document.execCommand('insertText', false, '  ');
        updateWordCount();
        return;
      }
    }

    // Code block escape with Shift+Enter
    if (e.key === 'Enter' && e.shiftKey) {
      const codeBlock = sel.anchorNode?.closest?.('.code-block') || sel.anchorNode?.parentElement?.closest?.('.code-block');
      if (codeBlock) {
        e.preventDefault();
        const nextLine = document.createElement('div');
        nextLine.innerHTML = '<br>';
        codeBlock.insertAdjacentElement('afterend', nextLine);
        const range = document.createRange();
        range.setStart(nextLine, 0);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        updateWordCount();
        return;
      }
    }

    // Checkbox continuation with Enter
    if (e.key === 'Enter') {
      const todoLine = sel.anchorNode?.closest?.('.todo-line') || sel.anchorNode?.parentElement?.closest?.('.todo-line');
      if (todoLine) {
        e.preventDefault();
        const textSpan = todoLine.querySelector('.todo-text');
        const currentText = textSpan ? textSpan.innerText.trim() : '';
        if (!currentText) {
          // If empty todo item, pressing enter converts it to a regular line
          const emptyLine = document.createElement('div');
          emptyLine.innerHTML = '<br>';
          modalEditor.replaceChild(emptyLine, todoLine);
          const range = document.createRange();
          range.setStart(emptyLine, 0);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        } else {
          // Create next checkbox line
          const nextLine = document.createElement('div');
          nextLine.className = 'todo-line';
          nextLine.innerHTML = `<input type="checkbox" class="todo-check" contenteditable="false"><span class="todo-text"></span>`;
          todoLine.insertAdjacentElement('afterend', nextLine);
          const nextSpan = nextLine.querySelector('.todo-text');
          nextSpan.focus();
          const range = document.createRange();
          range.setStart(nextSpan, 0);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        }
        updateWordCount();
        updateModalProgressBar();
      }
    }
  });

  // Paste plain text cleanly into modalEditor
  modalEditor.addEventListener('paste', (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, text);
    updateWordCount();
    updateModalProgressBar();
  });

  modalEditor.addEventListener('input', () => {
    updateWordCount();
    updateModalProgressBar();
  });

  let activeCardForMorph = null;
  let isAnimatingModal = false;

  function animateModalOpen(sourceEl) {
    if (isAnimatingModal) return;
    isAnimatingModal = true;

    const modalCard = noteModal.querySelector('.modal-card');
    noteModal.style.display = 'flex';

    if (!modalCard) {
      isAnimatingModal = false;
      return;
    }

    const sourceRect = sourceEl ? sourceEl.getBoundingClientRect() : null;
    const targetRect = modalCard.getBoundingClientRect();

    if (sourceRect && sourceRect.width > 0 && sourceRect.height > 0) {
      modalCard.style.transformOrigin = 'top left';

      const scaleX = Math.max(sourceRect.width / targetRect.width, 0.05);
      const scaleY = Math.max(sourceRect.height / targetRect.height, 0.05);
      const translateX = sourceRect.left - targetRect.left;
      const translateY = sourceRect.top - targetRect.top;

      // Animate backdrop fade and blur
      noteModal.animate(
        [
          { backgroundColor: 'rgba(0, 0, 0, 0)', backdropFilter: 'blur(0px)' },
          { backgroundColor: 'var(--modal-backdrop)', backdropFilter: 'blur(6px)' }
        ],
        { duration: 280, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
      );

      // Smooth fade for inner contents so scale doesn't distort text
      const modalHeader = modalCard.querySelector('.modal-header');
      const modalBody = modalCard.querySelector('.modal-body');
      const modalFooter = modalCard.querySelector('.modal-footer');
      [modalHeader, modalBody, modalFooter].forEach((el) => {
        if (el) {
          el.animate(
            [{ opacity: 0 }, { opacity: 1 }],
            { duration: 200, delay: 60, easing: 'ease-out', fill: 'both' }
          );
        }
      });

      // Morph modalCard expanding from source card to full modal
      const openAnim = modalCard.animate(
        [
          {
            transform: `translate(${translateX}px, ${translateY}px) scale(${scaleX}, ${scaleY})`,
            borderRadius: '16px',
            opacity: 0.85,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
          },
          {
            transform: 'translate(0px, 0px) scale(1, 1)',
            borderRadius: '20px',
            opacity: 1,
            boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.4)'
          }
        ],
        { duration: 290, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
      );

      openAnim.onfinish = () => {
        isAnimatingModal = false;
        modalCard.style.transform = '';
        modalCard.style.borderRadius = '';
      };
    } else {
      // Fallback smooth zoom from center
      modalCard.style.transformOrigin = 'center center';
      noteModal.animate(
        [{ opacity: 0 }, { opacity: 1 }],
        { duration: 240, easing: 'ease-out', fill: 'forwards' }
      );
      const openAnim = modalCard.animate(
        [
          { transform: 'scale(0.88) translateY(18px)', opacity: 0 },
          { transform: 'scale(1) translateY(0px)', opacity: 1 }
        ],
        { duration: 260, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'forwards' }
      );
      openAnim.onfinish = () => {
        isAnimatingModal = false;
        modalCard.style.transform = '';
      };
    }
  }

  function closeModal() {
    if (isAnimatingModal) return;
    if (noteModal.style.display === 'none') return;
    isAnimatingModal = true;

    const modalCard = noteModal.querySelector('.modal-card');
    const targetCard = currentEditingId
      ? document.querySelector(`.note-card[data-id="${currentEditingId}"]`)
      : (activeCardForMorph || newNoteBtn);

    const sourceRect = modalCard ? modalCard.getBoundingClientRect() : null;
    const targetRect = targetCard ? targetCard.getBoundingClientRect() : null;

    if (modalCard && sourceRect && targetRect && targetRect.width > 0 && targetRect.height > 0) {
      modalCard.style.transformOrigin = 'top left';

      const scaleX = Math.max(targetRect.width / sourceRect.width, 0.05);
      const scaleY = Math.max(targetRect.height / sourceRect.height, 0.05);
      const translateX = targetRect.left - sourceRect.left;
      const translateY = targetRect.top - sourceRect.top;

      // Animate backdrop fade out
      noteModal.animate(
        [
          { backgroundColor: 'var(--modal-backdrop)', backdropFilter: 'blur(6px)' },
          { backgroundColor: 'rgba(0, 0, 0, 0)', backdropFilter: 'blur(0px)' }
        ],
        { duration: 230, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'forwards' }
      );

      // Fade out internal contents quickly for clean morph collapse
      const modalHeader = modalCard.querySelector('.modal-header');
      const modalBody = modalCard.querySelector('.modal-body');
      const modalFooter = modalCard.querySelector('.modal-footer');
      [modalHeader, modalBody, modalFooter].forEach((el) => {
        if (el) {
          el.animate(
            [{ opacity: 1 }, { opacity: 0 }],
            { duration: 110, easing: 'ease-in', fill: 'both' }
          );
        }
      });

      // Morph modalCard closing back down into target card
      const closeAnim = modalCard.animate(
        [
          {
            transform: 'translate(0px, 0px) scale(1, 1)',
            borderRadius: '20px',
            opacity: 1
          },
          {
            transform: `translate(${translateX}px, ${translateY}px) scale(${scaleX}, ${scaleY})`,
            borderRadius: '16px',
            opacity: 0.15
          }
        ],
        { duration: 240, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'forwards' }
      );

      closeAnim.onfinish = () => {
        noteModal.style.display = 'none';
        modalCard.style.transform = '';
        modalCard.style.borderRadius = '';
        currentEditingId = null;
        activeCardForMorph = null;
        isAnimatingModal = false;
      };
    } else {
      // Fallback fade out
      noteModal.animate(
        [{ opacity: 1 }, { opacity: 0 }],
        { duration: 180, easing: 'ease-in', fill: 'forwards' }
      );
      const closeAnim = modalCard ? modalCard.animate(
        [
          { transform: 'scale(1) translateY(0px)', opacity: 1 },
          { transform: 'scale(0.9) translateY(14px)', opacity: 0 }
        ],
        { duration: 180, easing: 'ease-in', fill: 'forwards' }
      ) : null;

      const finishHandler = () => {
        noteModal.style.display = 'none';
        currentEditingId = null;
        activeCardForMorph = null;
        isAnimatingModal = false;
      };

      if (closeAnim) closeAnim.onfinish = finishHandler;
      else finishHandler();
    }
  }

  function openNewModal(triggerEl = null) {
    currentEditingId = null;
    activeCardForMorph = triggerEl || newNoteBtn;

    modalTitle.value = '';
    setEditorContent('');
    modalTags.value = '';
    isModalPinned = false;
    setColor('default');
    updatePinButtonUi();
    updateWordCount();
    updateModalProgressBar();

    if (modalFolder) {
      if (activeFolderId) {
        modalFolder.value = String(activeFolderId);
      } else {
        const defaultFolder = folders.find(f => f.is_default) || folders[0];
        modalFolder.value = defaultFolder ? String(defaultFolder.id) : '';
      }
    }

    modalDeleteBtn.style.display = 'none';
    downloadTxtBtn.style.display = 'none';
    noteDatesEl.style.display = 'none';
    modalSaveBtn.textContent = 'Save Note';

    animateModalOpen(activeCardForMorph);
    setTimeout(() => modalTitle.focus(), 250);
  }

  function openEditModal(noteId, clickedCard = null) {
    const note = notes.find((n) => n.id === noteId);
    if (!note) return;

    currentEditingId = noteId;
    activeCardForMorph = clickedCard || document.querySelector(`.note-card[data-id="${noteId}"]`);

    modalTitle.value = note.title || '';
    setEditorContent(note.content || '');
    modalTags.value = (note.tags_list || []).join(', ');
    isModalPinned = !!note.is_pinned;
    setColor(note.color || 'default');
    updatePinButtonUi();
    updateWordCount();
    updateModalProgressBar();

    if (modalFolder) {
      const defaultFolder = folders.find(f => f.is_default) || folders[0];
      const defaultId = defaultFolder ? defaultFolder.id : '';
      modalFolder.value = String(note.folder_id || defaultId);
    }

    modalDeleteBtn.style.display = 'inline-flex';
    downloadTxtBtn.style.display = 'inline-flex';
    noteDatesEl.style.display = 'inline';
    noteDatesEl.textContent = `Updated ${formatDate(note.updated_at)}`;
    modalSaveBtn.textContent = 'Update Note';

    animateModalOpen(activeCardForMorph);
  }

  function setColor(color) {
    selectedColor = color || 'default';
    colorDots.forEach((dot) => {
      dot.classList.toggle('active', dot.getAttribute('data-color') === selectedColor);
    });
    const modalCard = noteModal.querySelector('.modal-card');
    if (modalCard) {
      modalCard.setAttribute('data-color', selectedColor);
    }
  }

  colorDots.forEach((dot) => {
    dot.addEventListener('click', () => {
      setColor(dot.getAttribute('data-color'));
    });
  });

  function updatePinButtonUi() {
    modalPinBtn.classList.toggle('active', isModalPinned);
    modalPinBtn.style.opacity = isModalPinned ? '1' : '0.5';
  }

  modalPinBtn.addEventListener('click', () => {
    isModalPinned = !isModalPinned;
    updatePinButtonUi();
  });

  function updateWordCount() {
    const text = getEditorContent().trim();
    const words = text ? text.split(/\s+/).length : 0;
    wordCountEl.textContent = `${words} ${words === 1 ? 'word' : 'words'}`;
  }

  // Save Note
  async function saveCurrentNote() {
    const title = modalTitle.value.trim() || 'Untitled Note';
    const content = getEditorContent();
    const tags = modalTags.value;
    const color = selectedColor;
    const is_pinned = isModalPinned;
    const defaultFolder = folders.find(f => f.is_default) || folders[0];
    const defaultId = defaultFolder ? defaultFolder.id : 1;
    const folder_id = modalFolder ? (parseInt(modalFolder.value, 10) || defaultId) : defaultId;

    const payload = { title, content, tags, color, is_pinned, folder_id };

    try {
      let res;
      if (currentEditingId) {
        res = await fetch(`/api/notes/${currentEditingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch('/api/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (res.status === 401) {
        handleUnauthorized();
        return;
      }

      if (!res.ok) throw new Error('Failed to save');
      showToast(currentEditingId ? 'Note updated successfully' : 'Note created successfully');
      closeModal();
      fetchNotes();
    } catch (err) {
      console.error(err);
      showToast('Error saving note');
    }
  }

  // Delete Note
  async function deleteCurrentNote() {
    if (!currentEditingId) return;
    if (!confirm('Are you sure you want to delete this note?')) return;

    try {
      const res = await fetch(`/api/notes/${currentEditingId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete');
      showToast('Note deleted');
      closeModal();
      fetchNotes();
    } catch (err) {
      console.error(err);
      showToast('Error deleting note');
    }
  }

  // Download Single Note as Text
  downloadTxtBtn.addEventListener('click', () => {
    const title = modalTitle.value.trim() || 'note';
    const content = getEditorContent();
    const tags = modalTags.value ? `\nTags: ${modalTags.value}` : '';
    const fullText = `${title}${tags}\n\n${content}`;
    
    const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/[^a-z0-9_-]/g, '_')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Downloaded text file');
  });

  // Modal Button Triggers
  newNoteBtn.addEventListener('click', () => openNewModal(newNoteBtn));
  emptyCreateBtn.addEventListener('click', () => openNewModal(emptyCreateBtn));
  modalCloseBtn.addEventListener('click', closeModal);
  modalCancelBtn.addEventListener('click', closeModal);
  modalSaveBtn.addEventListener('click', saveCurrentNote);
  modalDeleteBtn.addEventListener('click', deleteCurrentNote);

  // Close modal when clicking outside on backdrop
  noteModal.addEventListener('click', (e) => {
    if (e.target === noteModal) {
      closeModal();
    }
  });

  // Folder Management Modal Handlers
  function openCreateFolderModal(parentId = null) {
    currentEditingFolderId = null;
    folderModalTitle.textContent = 'New Folder';
    folderNameInput.value = '';
    folderModalError.textContent = '';
    folderModalError.style.display = 'none';
    updateFolderParentSelect(parentId);
    folderModal.style.display = 'flex';
    setTimeout(() => folderNameInput.focus(), 100);
  }

  function openRenameFolderModal(folderId, folderName, parentId = null) {
    currentEditingFolderId = folderId;
    folderModalTitle.textContent = 'Edit Folder';
    folderNameInput.value = folderName;
    folderModalError.textContent = '';
    folderModalError.style.display = 'none';
    updateFolderParentSelect(parentId);
    folderModal.style.display = 'flex';
    setTimeout(() => {
      folderNameInput.focus();
      folderNameInput.select();
    }, 100);
  }

  function closeFolderModal() {
    folderModal.style.display = 'none';
    currentEditingFolderId = null;
    folderModalError.textContent = '';
    folderModalError.style.display = 'none';
  }

  async function saveFolder() {
    const name = folderNameInput.value.trim();
    if (!name) {
      folderModalError.textContent = 'Please enter a folder name.';
      folderModalError.style.display = 'block';
      folderNameInput.focus();
      return;
    }

    const parentIdVal = folderParentSelect ? folderParentSelect.value : '';
    const parent_id = parentIdVal ? parseInt(parentIdVal, 10) : null;
    const payload = { name, parent_id };

    try {
      let res;
      if (currentEditingFolderId) {
        res = await fetch(`/api/folders/${currentEditingFolderId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch('/api/folders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      const result = await res.json();
      if (!res.ok) {
        folderModalError.textContent = result.error || 'Failed to save folder';
        folderModalError.style.display = 'block';
        return;
      }

      showToast(currentEditingFolderId ? 'Folder updated' : `Folder "${name}" created`);
      closeFolderModal();
      await fetchFolders();

      if (!currentEditingFolderId && result.id) {
        selectFolderFilter(result.id, result.path || result.name);
      } else {
        fetchNotes();
      }
    } catch (err) {
      console.error(err);
      folderModalError.textContent = 'Server error saving folder';
      folderModalError.style.display = 'block';
    }
  }

  async function deleteFolder(folderId, folderName) {
    if (!confirm(`Are you sure you want to delete folder "${folderName}"?\n\nAll notes inside will be moved to the Home folder.`)) {
      return;
    }

    try {
      const res = await fetch(`/api/folders/${folderId}`, { method: 'DELETE' });
      const result = await res.json();
      if (!res.ok) {
        showToast(result.error || 'Failed to delete folder');
        return;
      }

      showToast(`Folder "${folderName}" deleted. Notes moved to Home.`);
      if (activeFolderId === folderId) {
        selectFilter('all');
      } else {
        await fetchFolders();
        fetchNotes();
      }
    } catch (err) {
      console.error(err);
      showToast('Error deleting folder');
    }
  }

  if (newFolderBtn) newFolderBtn.addEventListener('click', openCreateFolderModal);
  if (folderModalCloseBtn) folderModalCloseBtn.addEventListener('click', closeFolderModal);
  if (folderModalCancelBtn) folderModalCancelBtn.addEventListener('click', closeFolderModal);
  if (folderModalSaveBtn) folderModalSaveBtn.addEventListener('click', saveFolder);
  if (folderNameInput) {
    folderNameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveFolder();
      }
    });
  }

  if (folderModal) {
    folderModal.addEventListener('click', (e) => {
      if (e.target === folderModal) {
        closeFolderModal();
      }
    });
  }

  // Backup & Restore
  backupMenuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    backupMenuBtn.closest('.dropdown-container').classList.toggle('open');
  });

  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-container').forEach((c) => c.classList.remove('open'));
  });

  exportJsonBtn.addEventListener('click', () => {
    window.location.href = '/api/export';
    showToast('Exporting notes backup...');
  });

  importFileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const json = JSON.parse(event.target.result);
          const res = await fetch('/api/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(json)
          });
          const result = await res.json();
          if (res.ok) {
            showToast(`Imported ${result.imported} notes successfully`);
            fetchNotes();
          } else {
            showToast('Import error: ' + (result.error || 'Failed'));
          }
        } catch {
          showToast('Invalid JSON backup file');
        }
      };
      reader.readAsText(file);
    } catch (err) {
      console.error(err);
      showToast('Error reading file');
    }
    e.target.value = '';
  });

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (folderModal && folderModal.style.display !== 'none') {
        closeFolderModal();
      } else if (noteModal.style.display !== 'none') {
        closeModal();
      } else if (searchInput.value) {
        searchInput.value = '';
        searchQuery = '';
        clearSearchBtn.style.display = 'none';
        isUniversalSearch = true;
        fetchNotes();
      }
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 'n' || e.key === 'N')) {
      e.preventDefault();
      openNewModal();
    }

    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      if (folderModal && folderModal.style.display !== 'none') {
        e.preventDefault();
        saveFolder();
      } else if (noteModal.style.display !== 'none') {
        e.preventDefault();
        saveCurrentNote();
      }
    }

    if (
      (e.key === '/' || ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K'))) &&
      noteModal.style.display === 'none' &&
      (!folderModal || folderModal.style.display === 'none') &&
      document.activeElement !== searchInput &&
      document.activeElement.tagName !== 'INPUT' &&
      document.activeElement.tagName !== 'TEXTAREA' &&
      !document.activeElement.isContentEditable
    ) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });

  // Auth Event Listeners
  if (tabLoginBtn) tabLoginBtn.addEventListener('click', () => switchAuthTab('login'));
  if (tabRegisterBtn) tabRegisterBtn.addEventListener('click', () => switchAuthTab('register'));
  if (tabForgotBtn) tabForgotBtn.addEventListener('click', () => switchAuthTab('forgot'));
  if (switchToForgotBtn) switchToForgotBtn.addEventListener('click', () => switchAuthTab('forgot'));
  if (switchToRegisterBtn) switchToRegisterBtn.addEventListener('click', () => switchAuthTab('register'));
  if (switchToLoginBtn1) switchToLoginBtn1.addEventListener('click', () => switchAuthTab('login'));
  if (switchToLoginBtn2) switchToLoginBtn2.addEventListener('click', () => switchAuthTab('login'));

  if (forgotBackToStep1Btn) {
    forgotBackToStep1Btn.addEventListener('click', () => {
      if (forgotStep1) forgotStep1.style.display = 'block';
      if (forgotStep2) forgotStep2.style.display = 'none';
      clearAuthErrors();
    });
  }

  if (loginForm) loginForm.addEventListener('submit', handleLogin);
  if (loginSubmitBtn) loginSubmitBtn.addEventListener('click', handleLogin);
  if (registerForm) registerForm.addEventListener('submit', handleRegister);
  if (registerSubmitBtn) registerSubmitBtn.addEventListener('click', handleRegister);
  if (forgotStep1Form) forgotStep1Form.addEventListener('submit', handleForgotStep1);
  if (forgotSendCodeBtn) forgotSendCodeBtn.addEventListener('click', handleForgotStep1);
  if (forgotStep2Form) forgotStep2Form.addEventListener('submit', handleResetPassword);
  if (resetSubmitBtn) resetSubmitBtn.addEventListener('click', handleResetPassword);

  if (userMenuBtn) {
    userMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      userProfileContainer.classList.toggle('open');
    });
  }

  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
  }

  // Initialize
  initTheme();
  if (!isGridView) {
    viewListBtn.classList.add('active');
    viewGridBtn.classList.remove('active');
  }
  checkAuth();
})();
