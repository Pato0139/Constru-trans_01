document.addEventListener('DOMContentLoaded', function() {
  const toggleBtn = document.getElementById('chat-widget-toggle');
  const chatBox = document.getElementById('chat-widget-box');
  const closeBtn = document.getElementById('chat-widget-close');
  const messagesContainer = document.getElementById('chat-widget-messages');
  const input = document.getElementById('chat-widget-input');
  const sendBtn = document.getElementById('chat-widget-send');

  // Abrir / Cerrar chat
  toggleBtn.addEventListener('click', function() {
    chatBox.classList.toggle('active');
  });

  closeBtn.addEventListener('click', function() {
    chatBox.classList.remove('active');
  });

  // Enviar mensaje con botón
  sendBtn.addEventListener('click', sendMessage);

  // Enviar mensaje con Enter
  input.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });

  let typingIndicator = null;

  function sendMessage() {
    const message = input.value.trim();
    if (!message) return;

    // Agregar mensaje del usuario
    addMessage(message, 'user');
    input.value = '';
    sendBtn.disabled = true;

    // Mostrar indicador de escribiendo
    showTypingIndicator();

    // Simular respuesta del bot
    fetch('/ia/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ mensaje: message })
    })
    .then(response => response.json())
    .then(data => {
      removeTypingIndicator();
      addMessage(data.respuesta, 'bot');
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

  function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    
    if (sender === 'bot') {
      messageDiv.innerHTML = `
        <div class="chat-message-avatar">
          <img src="/static/img/Logo1.jpeg" alt="Logo Constru-Trans" class="chat-message-logo">
        </div>
        <div class="chat-message-bubble">${escapeHtml(text)}</div>
      `;
    } else {
      messageDiv.innerHTML = `
        <div class="chat-message-bubble">${escapeHtml(text)}</div>
      `;
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
