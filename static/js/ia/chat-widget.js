
document.addEventListener('DOMContentLoaded', function() {
  const toggleBtn = document.getElementById('chat-widget-toggle');
  const chatBox = document.getElementById('chat-widget-box');
  const closeBtn = document.getElementById('chat-widget-close');
  const messagesContainer = document.getElementById('chat-widget-messages');
  const input = document.getElementById('chat-widget-input');
  const sendBtn = document.getElementById('chat-widget-send');

  // Configuración
  const STORAGE_KEY = 'constru-trans-chat-history';
  const SESSION_KEY = 'constru-trans-session-id';
  const MAX_MESSAGES = 20;
  let typingIndicator = null;
  let chatHistory = [];
  let sessionId = localStorage.getItem(SESSION_KEY) || generateSessionId();
  localStorage.setItem(SESSION_KEY, sessionId);

  // Cargar historial al iniciar
  loadChatHistory();

  // Abrir / Cerrar chat y guardar estado
  toggleBtn.addEventListener('click', function() {
    chatBox.classList.toggle('active');
    localStorage.setItem('constru-trans-chat-open', chatBox.classList.contains('active'));
  });

  closeBtn.addEventListener('click', function() {
    chatBox.classList.remove('active');
    localStorage.setItem('constru-trans-chat-open', 'false');
  });

  // Restaurar estado del chat al cargar
  const wasOpen = localStorage.getItem('constru-trans-chat-open');
  if (wasOpen === 'true') {
    chatBox.classList.add('active');
  }

  // Enviar mensaje con botón
  sendBtn.addEventListener('click', sendMessage);

  // Enviar mensaje con Enter
  input.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });

  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  function loadChatHistory() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        chatHistory = JSON.parse(saved);
        // Renderizar mensajes guardados
        chatHistory.forEach(msg => addMessageToDOM(msg.text, msg.sender, false, msg.messageId));
      }
    } catch (e) {
      console.error('Error al cargar historial:', e);
      chatHistory = [];
    }
  }

  function saveChatHistory() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
    } catch (e) {
      console.error('Error al guardar historial:', e);
    }
  }

  function cleanOldMessages() {
    if (chatHistory.length > MAX_MESSAGES) {
      // Eliminar los mensajes más antiguos
      const messagesToRemove = chatHistory.length - MAX_MESSAGES;
      chatHistory = chatHistory.slice(messagesToRemove);
      // Volver a renderizar
      messagesContainer.innerHTML = '';
      chatHistory.forEach(msg => addMessageToDOM(msg.text, msg.sender, false, msg.messageId));
      saveChatHistory();
    }
  }

  function sendMessage() {
    const message = input.value.trim();
    if (!message) return;

    // Agregar mensaje del usuario
    addMessage(message, 'user');
    input.value = '';
    sendBtn.disabled = true;

    // Mostrar indicador de escribiendo
    showTypingIndicator();

    // Enviar a backend con historial
    fetch('/ia/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ 
        mensaje: message,
        historial: chatHistory.slice(-10), // Enviar últimos 10 mensajes para contexto
        session_id: sessionId
      })
    })
    .then(response => response.json())
    .then(data => {
      removeTypingIndicator();
      addMessage(data.respuesta, 'bot', data.message_id);
    })
    .catch(error => {
      removeTypingIndicator();
      addMessage('Lo siento, no pude responder en este momento.', 'bot');
      console.error('Error:', error);
    })
    .finally(() => {
      sendBtn.disabled = false;
      input.focus();
    });
  }



  function showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message bot';
    messageDiv.id = 'typing-indicator';
    messageDiv.innerHTML = `
      <div class="chat-message-avatar">
        <img src="/static/img/Logo1.jpeg" alt="Logo Constru-Trans" class="chat-message-logo">
      </div>
      <div class="chat-message-bubble">
        <span class="typing-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </span>
      </div>
    `;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    typingIndicator = messageDiv;
  }

  function removeTypingIndicator() {
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
  }

  function addMessage(text, sender, messageId = null) {
    addMessageToDOM(text, sender, true, messageId);
  }

  function addMessageToDOM(text, sender, save = true, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    if (messageId) {
      messageDiv.dataset.messageId = messageId;
    }
    
    if (sender === 'bot') {
      messageDiv.innerHTML = `
        <div class="chat-message-avatar">
          <img src="/static/img/Logo1.jpeg" alt="Logo Constru-Trans" class="chat-message-logo">
        </div>
        <div class="chat-message-content">
          <div class="chat-message-bubble">${escapeHtml(text)}</div>
        </div>
      `;
    } else {
      messageDiv.innerHTML = `
        <div class="chat-message-bubble">${escapeHtml(text)}</div>
      `;
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Guardar en historial
    if (save) {
      chatHistory.push({
        text: text,
        sender: sender,
        messageId: messageId,
        timestamp: new Date().toISOString()
      });
      cleanOldMessages();
      saveChatHistory();
    }
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});

