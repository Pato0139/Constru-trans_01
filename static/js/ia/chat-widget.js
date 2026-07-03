/**
 * Inicializa el widget de chat de IA
 */
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

  /**
   * Genera un ID único de sesión
   * @returns {string} ID de sesión
   */
  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Carga el historial de chat desde localStorage
   */
  function loadChatHistory() {
    try {
      // Clear ALL chat-related localStorage items to fix old issues!
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('constru-trans-chat')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));
      chatHistory = [];
    } catch (e) {
      console.error('Error al cargar historial:', e);
      chatHistory = [];
    }
  }

  /**
   * Limpia el texto eliminando guiones al final de las líneas
   * @param {string} text - Texto a limpiar
   * @returns {string} Texto limpio
   */
  function cleanText(text) {
    return text.split('\n').map(line => {
      // Remove trailing dashes but keep the line
      let cleanedLine = line.replace(/\s*-$/, '');
      // Also remove any leading/trailing whitespace that's not needed
      cleanedLine = cleanedLine.trimEnd();
      return cleanedLine;
    }).join('\n');
  }

  /**
   * Guarda el historial de chat en localStorage
   */
  function saveChatHistory() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
    } catch (e) {
      console.error('Error al guardar historial:', e);
    }
  }

  /**
   * Limpia los mensajes antiguos cuando se supera el máximo
   */
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

  /**
   * Envía un mensaje al backend de IA
   */
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
    .then(response => {
      if (!response.ok) {
        throw new Error('Error en la respuesta del servidor');
      }
      return response.json();
    })
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

  /**
   * Muestra el indicador de "escribiendo"
   */
  function showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message bot';
    messageDiv.id = 'typing-indicator';
    messageDiv.innerHTML = `
      <div class="chat-message-avatar">
        <img src="/static/img/Logo1.jpeg" alt="Logo Constru-Trans" class="chat-message-logo" loading="lazy">
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

  /**
   * Elimina el indicador de "escribiendo"
   */
  function removeTypingIndicator() {
    if (typingIndicator) {
      typingIndicator.remove();
      typingIndicator = null;
    }
  }

  /**
   * Agrega un mensaje al chat
   * @param {string} text - Texto del mensaje
   * @param {string} sender - Remitente ('user' o 'bot')
   * @param {string} [messageId=null] - ID del mensaje
   */
  function addMessage(text, sender, messageId = null) {
    addMessageToDOM(text, sender, true, messageId);
  }

  /**
   * Agrega un mensaje al DOM
   * @param {string} text - Texto del mensaje
   * @param {string} sender - Remitente ('user' o 'bot')
   * @param {boolean} [save=true] - Si debe guardarse en historial
   * @param {string} [messageId=null] - ID del mensaje
   */
  function addMessageToDOM(text, sender, save = true, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    if (messageId) {
      messageDiv.dataset.messageId = messageId;
    }
    
    // Clean text and escape HTML
    const cleanedText = cleanText(text);
    const safeText = escapeHtml(cleanedText);
    
    if (sender === 'bot') {
      messageDiv.innerHTML = `
        <div class="chat-message-avatar">
          <img src="/static/img/Logo1.jpeg" alt="Logo Constru-Trans" class="chat-message-logo" loading="lazy">
        </div>
        <div class="chat-message-content">
          <div class="chat-message-bubble">${safeText}</div>
        </div>
      `;
    } else {
      messageDiv.innerHTML = `
        <div class="chat-message-bubble">${safeText}</div>
      `;
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Guardar en historial
    if (save) {
      chatHistory.push({
        text: cleanedText,
        sender: sender,
        messageId: messageId,
        timestamp: new Date().toISOString()
      });
      cleanOldMessages();
      saveChatHistory();
    }
  }

  /**
   * Obtiene el valor de una cookie
   * @param {string} name - Nombre de la cookie
   * @returns {string|null} Valor de la cookie
   */
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

  /**
   * Escapa HTML para prevenir XSS
   * @param {string} text - Texto a escapar
   * @returns {string} Texto seguro
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});

